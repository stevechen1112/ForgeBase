#!/usr/bin/env python3
"""Idempotently prepare one receiving-only Resend subdomain for DNS setup."""

from __future__ import annotations

import argparse
import http.client
import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

API_HOST = "api.resend.com"
SCHEMA_VERSION = 1


class ProvisionError(RuntimeError):
    pass


def _domain(value: str, root_domain: str = "premierbiz.com.tw") -> str:
    normalized = value.strip().rstrip(".").lower()
    root = root_domain.strip().rstrip(".").lower()
    labels = normalized.split(".")
    if (
        not normalized.isascii()
        or len(normalized) > 253
        or len(labels) < 3
        or normalized == root
        or not normalized.endswith(f".{root}")
        or not all(
            label
            and len(label) <= 63
            and label[0].isalnum()
            and label[-1].isalnum()
            and all(char.isalnum() or char == "-" for char in label)
            for label in labels
        )
    ):
        raise ValueError("inbound domain must be a valid subdomain")
    return normalized


def _request(
    api_key: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "ForgeBase-Inbound-Provisioner/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    connection = http.client.HTTPSConnection(API_HOST, timeout=15)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise ProvisionError(f"Resend API returned HTTP {response.status}")
        result = json.loads(response.read())
    except OSError as exc:
        raise ProvisionError("Resend API request failed") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProvisionError("Resend API returned invalid JSON") from exc
    finally:
        connection.close()
    if not isinstance(result, dict):
        raise ProvisionError("Resend API returned an invalid object")
    return result


def _records(details: dict[str, Any]) -> list[dict[str, Any]]:
    records = details.get("records") or []
    result = []
    for record in records:
        if not isinstance(record, dict):
            continue
        record_type = str(record.get("type") or "").upper()
        name = str(record.get("name") or "").strip()
        value = str(record.get("value") or "").strip()
        if (
            record_type not in {"MX", "TXT", "CNAME"}
            or not name
            or not value
            or any(char in name + value for char in "\r\n")
        ):
            continue
        result.append(
            {
                "purpose": str(record.get("record") or "unknown"),
                "type": record_type,
                "name": name,
                "value": value,
                "priority": record.get("priority"),
                "ttl": str(record.get("ttl") or "Auto"),
                "status": str(record.get("status") or "unknown"),
            }
        )
    return result


def provision(
    *,
    api_key: str,
    inbound_domain: str,
    root_domain: str = "premierbiz.com.tw",
    request: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("RESEND_API_KEY is required")
    name = _domain(inbound_domain, root_domain)
    call = request or (lambda method, path, payload=None: _request(api_key, method, path, payload))
    listing = call("GET", "/domains?limit=100")
    if listing.get("has_more"):
        raise ProvisionError("Resend domain inventory exceeds the audited safety limit")
    rows = listing.get("data") or []
    existing = next(
        (
            row
            for row in rows
            if isinstance(row, dict)
            and str(row.get("name") or "").strip().lower() == name
        ),
        None,
    )
    operation = "reused"
    if existing is None:
        existing = call(
            "POST",
            "/domains",
            {
                "name": name,
                "region": "ap-northeast-1",
                "capabilities": {"sending": "disabled", "receiving": "enabled"},
            },
        )
        operation = "created"
    domain_id = str(existing.get("id") or "")
    if not domain_id:
        raise ProvisionError("Resend domain id is missing")
    capabilities = existing.get("capabilities") or {}
    if capabilities.get("sending") != "disabled" or capabilities.get("receiving") != "enabled":
        call(
            "PATCH",
            f"/domains/{quote(domain_id, safe='')}",
            {"capabilities": {"sending": "disabled", "receiving": "enabled"}},
        )
        operation = "updated"
    details = call("GET", f"/domains/{quote(domain_id, safe='')}")
    if str(details.get("name") or "").strip().lower() != name:
        raise ProvisionError("Resend returned the wrong domain")
    capabilities = details.get("capabilities") or {}
    dns_records = _records(details)
    ready = (
        capabilities.get("sending") == "disabled"
        and capabilities.get("receiving") == "enabled"
        and bool(dns_records)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": operation,
        "domain": name,
        "status": str(details.get("status") or "unknown"),
        "capabilities": {
            "sending": str(capabilities.get("sending") or "unknown"),
            "receiving": str(capabilities.get("receiving") or "unknown"),
        },
        "dns_records": dns_records,
        "assessment": {
            "status": "dns_action_required" if ready else "failed",
            "ready_for_dns_configuration": ready,
        },
        "privacy": {
            "api_key_in_report": False,
            "provider_domain_id_in_report": False,
            "email_addresses_in_report": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbound-domain", required=True)
    parser.add_argument("--root-domain", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = provision(
        api_key=os.environ.get("RESEND_API_KEY", ""),
        inbound_domain=args.inbound_domain,
        root_domain=args.root_domain,
    )
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0 if report["assessment"]["ready_for_dns_configuration"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
