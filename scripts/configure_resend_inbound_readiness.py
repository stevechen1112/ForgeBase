#!/usr/bin/env python3
"""Idempotently verify the Resend inbound domain and enable inbound webhooks."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

API_HOST = "api.resend.com"
SCHEMA_VERSION = 1
REQUIRED_OUTBOUND_EVENTS = {
    "email.sent",
    "email.delivered",
    "email.bounced",
    "email.complained",
}
REQUIRED_INBOUND_EVENT = "email.received"


class ConfigureError(RuntimeError):
    """Safe provider-configuration failure without response-body disclosure."""


def _domain(value: str, root_domain: str) -> str:
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


def _endpoint(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("webhook endpoint is invalid") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("webhook endpoint is invalid")
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
        "User-Agent": "ForgeBase-Inbound-Readiness/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    connection = http.client.HTTPSConnection(API_HOST, timeout=15)
    try:
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        if not 200 <= response.status < 300:
            raise ConfigureError(f"Resend API returned HTTP {response.status}")
        raw = response.read()
        result = json.loads(raw) if raw else {}
    except OSError as exc:
        raise ConfigureError("Resend API request failed") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigureError("Resend API returned invalid JSON") from exc
    finally:
        connection.close()
    if not isinstance(result, dict):
        raise ConfigureError("Resend API returned an invalid object")
    return result


def _list_rows(payload: dict[str, Any], resource: str) -> list[dict[str, Any]]:
    if payload.get("has_more"):
        raise ConfigureError(f"Resend {resource} inventory exceeds the safety limit")
    rows = payload.get("data")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ConfigureError(f"Resend {resource} inventory is invalid")
    return rows


def configure(
    *,
    api_key: str,
    inbound_domain: str,
    root_domain: str,
    webhook_endpoint: str,
    attempts: int = 24,
    poll_seconds: float = 5,
    request: Callable[..., dict[str, Any]] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not api_key.strip():
        raise ValueError("RESEND_API_KEY is required")
    if attempts < 1 or attempts > 60:
        raise ValueError("attempts must be between 1 and 60")
    if poll_seconds < 0 or poll_seconds > 30:
        raise ValueError("poll_seconds must be between 0 and 30")
    domain_name = _domain(inbound_domain, root_domain)
    endpoint = _endpoint(webhook_endpoint)
    call = request or (
        lambda method, path, payload=None: _request(api_key, method, path, payload)
    )
    operations: list[str] = []

    domains = _list_rows(call("GET", "/domains?limit=100"), "domain")
    matching_domains = [
        row
        for row in domains
        if str(row.get("name") or "").strip().rstrip(".").lower() == domain_name
    ]
    if len(matching_domains) != 1:
        raise ConfigureError("expected exactly one Resend inbound domain")
    domain = matching_domains[0]
    domain_id = str(domain.get("id") or "")
    if not domain_id:
        raise ConfigureError("Resend inbound domain id is missing")
    capabilities = domain.get("capabilities") or {}
    if capabilities.get("sending") != "disabled" or capabilities.get("receiving") != "enabled":
        call(
            "PATCH",
            f"/domains/{quote(domain_id, safe='')}",
            {"capabilities": {"sending": "disabled", "receiving": "enabled"}},
        )
        operations.append("domain_capabilities_aligned")

    details = call("GET", f"/domains/{quote(domain_id, safe='')}")
    if str(details.get("name") or "").strip().rstrip(".").lower() != domain_name:
        raise ConfigureError("Resend returned the wrong inbound domain")
    capabilities = details.get("capabilities") or {}
    status = str(details.get("status") or "unknown")
    if status not in {"verified", "pending"}:
        call("POST", f"/domains/{quote(domain_id, safe='')}/verify")
        operations.append("domain_verification_triggered")
    if status != "verified":
        for attempt in range(attempts):
            details = call("GET", f"/domains/{quote(domain_id, safe='')}")
            status = str(details.get("status") or "unknown")
            capabilities = details.get("capabilities") or {}
            if status == "verified":
                break
            if attempt + 1 < attempts:
                sleep(poll_seconds)

    webhooks = _list_rows(call("GET", "/webhooks?limit=100"), "webhook")
    matching_webhooks = [
        row
        for row in webhooks
        if str(row.get("endpoint") or "").strip().rstrip("/") == endpoint
    ]
    if len(matching_webhooks) != 1:
        raise ConfigureError("expected exactly one matching Resend webhook")
    webhook = matching_webhooks[0]
    webhook_id = str(webhook.get("id") or "")
    if not webhook_id:
        raise ConfigureError("Resend webhook id is missing")
    existing_events = {
        str(event) for event in (webhook.get("events") or []) if str(event).strip()
    }
    desired_events = sorted(existing_events | {REQUIRED_INBOUND_EVENT})
    if (
        set(desired_events) != existing_events
        or str(webhook.get("status") or "") != "enabled"
    ):
        call(
            "PATCH",
            f"/webhooks/{quote(webhook_id, safe='')}",
            {"endpoint": endpoint, "events": desired_events, "status": "enabled"},
        )
        operations.append("webhook_events_aligned")

    final_webhooks = _list_rows(call("GET", "/webhooks?limit=100"), "webhook")
    final_matches = [
        row
        for row in final_webhooks
        if str(row.get("endpoint") or "").strip().rstrip("/") == endpoint
        and str(row.get("status") or "") == "enabled"
    ]
    final_events = {
        str(event)
        for row in final_matches
        for event in (row.get("events") or [])
        if str(event).strip()
    }
    outbound_ready = REQUIRED_OUTBOUND_EVENTS <= final_events
    inbound_ready = REQUIRED_INBOUND_EVENT in final_events
    capabilities_ready = (
        capabilities.get("sending") == "disabled"
        and capabilities.get("receiving") == "enabled"
    )
    passed = status == "verified" and capabilities_ready and outbound_ready and inbound_ready
    blockers = []
    if status != "verified":
        blockers.append("inbound_domain_not_verified")
    if not capabilities_ready:
        blockers.append("inbound_domain_capabilities_not_aligned")
    if not outbound_ready:
        blockers.append("outbound_webhook_events_incomplete")
    if not inbound_ready:
        blockers.append("inbound_webhook_event_missing")

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": operations or ["already_aligned"],
        "domain": {
            "name": domain_name,
            "status": status,
            "sending": str(capabilities.get("sending") or "unknown"),
            "receiving": str(capabilities.get("receiving") or "unknown"),
        },
        "webhook": {
            "endpoint": endpoint,
            "status": "enabled" if final_matches else "missing",
            "events": sorted(final_events),
        },
        "assessment": {
            "status": "passed" if passed else "attention_required",
            "domain_verified": status == "verified",
            "outbound_webhook_ready": outbound_ready,
            "inbound_webhook_ready": inbound_ready,
            "blockers": blockers,
        },
        "privacy": {
            "api_key_in_report": False,
            "provider_ids_in_report": False,
            "signing_secret_in_report": False,
            "dns_record_values_in_report": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbound-domain", required=True)
    parser.add_argument("--root-domain", required=True)
    parser.add_argument("--webhook-endpoint", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--attempts", type=int, default=24)
    parser.add_argument("--poll-seconds", type=float, default=5)
    args = parser.parse_args()
    report = configure(
        api_key=os.environ.get("RESEND_API_KEY", ""),
        inbound_domain=args.inbound_domain,
        root_domain=args.root_domain,
        webhook_endpoint=args.webhook_endpoint,
        attempts=args.attempts,
        poll_seconds=args.poll_seconds,
    )
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return 0 if report["assessment"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
