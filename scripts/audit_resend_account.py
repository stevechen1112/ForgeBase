#!/usr/bin/env python3
"""Read-only, redacted audit of Resend domain and webhook readiness."""

from __future__ import annotations

import argparse
import http.client
import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode, urlsplit

API_HOST = "api.resend.com"
OUTBOUND_EVENTS = {
    "email.sent",
    "email.delivered",
    "email.bounced",
    "email.complained",
}
SCHEMA_VERSION = 1


class ResendAuditError(RuntimeError):
    """Safe provider-audit failure that never includes response content."""


def _normalize_domain(value: str) -> str:
    normalized = value.strip().rstrip(".").lower()
    labels = normalized.split(".")
    if (
        not normalized.isascii()
        or len(normalized) > 253
        or len(labels) < 2
        or not all(
            label
            and len(label) <= 63
            and label[0].isalnum()
            and label[-1].isalnum()
            and all(char.isalnum() or char == "-" for char in label)
            for label in labels
        )
    ):
        raise ValueError("expected sending domain is invalid")
    return normalized


def _normalize_endpoint(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("expected webhook endpoint is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("expected webhook endpoint is invalid")
    return normalized


def _provider_get(api_key: str, path: str) -> dict[str, Any]:
    connection = http.client.HTTPSConnection(API_HOST, timeout=15)
    try:
        connection.request(
            "GET",
            path,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
                "User-Agent": "ForgeBase-ReadOnly-Audit/1.0",
            },
        )
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise ResendAuditError(f"Resend API returned HTTP {response.status}")
        payload = json.loads(response.read())
    except OSError as exc:
        raise ResendAuditError("Resend API request failed") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ResendAuditError("Resend API returned invalid JSON") from exc
    finally:
        connection.close()
    if not isinstance(payload, dict):
        raise ResendAuditError("Resend API returned an invalid object")
    return payload


def _list_all(
    path: str,
    get_json: Callable[[str], dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    after: str | None = None
    for _page in range(100):
        query = {"limit": 100}
        if after:
            query["after"] = after
        payload = get_json(f"{path}?{urlencode(query)}")
        page = payload.get("data")
        if not isinstance(page, list) or not all(isinstance(row, dict) for row in page):
            raise ResendAuditError("Resend API list response is invalid")
        rows.extend(page)
        if not payload.get("has_more"):
            return rows
        if not page or not isinstance(page[-1].get("id"), str):
            raise ResendAuditError("Resend API pagination cursor is missing")
        after = page[-1]["id"]
    raise ResendAuditError("Resend API pagination exceeded the safety limit")


def build_report(
    *,
    api_key: str,
    expected_sending_domain: str,
    expected_webhook_endpoint: str,
    get_json: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("RESEND_API_KEY is required")
    domain_name = _normalize_domain(expected_sending_domain)
    webhook_endpoint = _normalize_endpoint(expected_webhook_endpoint)
    getter = get_json or (lambda path: _provider_get(api_key, path))

    raw_domains = _list_all("/domains", getter)
    raw_webhooks = _list_all("/webhooks", getter)

    matching_domains: list[dict[str, Any]] = []
    for row in raw_domains:
        name = str(row.get("name") or "").strip().lower()
        capabilities = row.get("capabilities") or {}
        if name == domain_name:
            matching_domains.append(
                {
                    "status": str(row.get("status") or "unknown"),
                    "region": str(row.get("region") or "unknown"),
                    "sending": str(capabilities.get("sending") or "unknown"),
                    "receiving": str(capabilities.get("receiving") or "unknown"),
                }
            )

    matching_webhooks: list[dict[str, Any]] = []
    for row in raw_webhooks:
        endpoint = str(row.get("endpoint") or "").strip().rstrip("/")
        events = row.get("events") or []
        if endpoint == webhook_endpoint:
            matching_webhooks.append(
                {
                    "status": str(row.get("status") or "unknown"),
                    "events": sorted(str(event) for event in events if event),
                }
            )

    matching_domain = matching_domains[0] if matching_domains else None
    sending_domain_ready = bool(
        matching_domain
        and matching_domain["status"] == "verified"
        and matching_domain["sending"] == "enabled"
    )
    enabled_matching_webhooks = [
        row
        for row in matching_webhooks
        if row["status"] == "enabled"
    ]
    enabled_events = {
        event for row in enabled_matching_webhooks for event in row["events"]
    }
    missing_outbound_events = sorted(OUTBOUND_EVENTS - enabled_events)
    outbound_webhook_ready = not missing_outbound_events
    inbound_webhook_ready = "email.received" in enabled_events
    blockers = []
    if not sending_domain_ready:
        blockers.append("sending_domain_not_ready")
    if not outbound_webhook_ready:
        blockers.append("outbound_webhook_events_incomplete")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": "read_only",
        "expected": {
            "sending_domain": domain_name,
            "webhook_endpoint": webhook_endpoint,
        },
        "domains": {
            "total_count": len(raw_domains),
            "expected_domain_matches": matching_domains,
            "nonmatching_count": len(raw_domains) - len(matching_domains),
        },
        "webhooks": {
            "total_count": len(raw_webhooks),
            "expected_endpoint_matches": matching_webhooks,
            "nonmatching_count": len(raw_webhooks) - len(matching_webhooks),
        },
        "assessment": {
            "status": "passed" if not blockers else "attention_required",
            "sending_domain_ready": sending_domain_ready,
            "outbound_webhook_ready": outbound_webhook_ready,
            "inbound_webhook_ready": inbound_webhook_ready,
            "missing_outbound_events": missing_outbound_events,
            "blockers": blockers,
        },
        "privacy": {
            "api_key_in_report": False,
            "dns_record_values_in_report": False,
            "email_addresses_in_report": False,
            "provider_ids_in_report": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-sending-domain", required=True)
    parser.add_argument("--expected-webhook-endpoint", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = build_report(
        api_key=os.environ.get("RESEND_API_KEY", ""),
        expected_sending_domain=args.expected_sending_domain,
        expected_webhook_endpoint=args.expected_webhook_endpoint,
    )
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
