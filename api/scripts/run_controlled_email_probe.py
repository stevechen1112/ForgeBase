"""Send one allowlisted internal email and verify provider plus webhook delivery."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from app.core.config import settings
from app.db.session import get_session_ctx
from app.models.email_delivery import EmailDeliveryEvent
from app.services.email_governance import normalize_email
from app.services.email_service import EmailDeliveryResult, send_email_result
from sqlmodel import select

SCHEMA_VERSION = 1
PROBE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
SUCCESS_EVENTS = {"delivered", "opened", "clicked"}
FAILURE_EVENTS = {"bounced", "complained", "failed", "suppressed"}


class ControlledProbeError(RuntimeError):
    pass


def _exact_internal_addresses() -> set[str]:
    return {
        normalize_email(value)
        for value in settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST.split(",")
        if "@" in value and normalize_email(value)
    }


def _validate(recipient: str, probe_id: str) -> str:
    normalized = normalize_email(recipient)
    if not PROBE_ID.fullmatch(probe_id):
        raise ControlledProbeError("probe_id_invalid")
    if normalized not in _exact_internal_addresses():
        raise ControlledProbeError("recipient_not_exactly_internal_allowlisted")
    if normalized != normalize_email(settings.EMAIL_FROM):
        raise ControlledProbeError("recipient_must_match_verified_internal_sender")
    if settings.EMAIL_DRY_RUN:
        raise ControlledProbeError("email_dry_run_enabled")
    if settings.EMAIL_EXTERNAL_DELIVERY_ENABLED or settings.OUTREACH_SEND_ENABLED:
        raise ControlledProbeError("general_delivery_switches_must_remain_closed")
    if not settings.RESEND_API_KEY.strip():
        raise ControlledProbeError("resend_not_configured")
    if not settings.RESEND_WEBHOOK_SECRET.strip():
        raise ControlledProbeError("resend_webhook_not_configured")
    return normalized


async def _provider_last_event(message_id: str) -> str | None:
    encoded_id = quote(message_id, safe="")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.resend.com/emails/{encoded_id}",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Accept": "application/json",
                    "User-Agent": "ForgeBase-Controlled-Probe/1.0",
                },
            )
    except httpx.RequestError:
        return None
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    event = str(payload.get("last_event") or "").strip().lower()
    return event or None


async def _webhook_events(message_id: str) -> set[str]:
    async with get_session_ctx() as db:
        rows = list(
            (
                await db.exec(
                    select(EmailDeliveryEvent.event_type).where(
                        EmailDeliveryEvent.provider_message_id == message_id
                    )
                )
            ).all()
        )
    return {str(value).removeprefix("email.").lower() for value in rows}


async def run_probe(
    *,
    recipient: str,
    probe_id: str,
    attempts: int = 31,
    interval_seconds: float = 3,
    sender: Callable[..., Awaitable[EmailDeliveryResult]] | None = None,
    provider_lookup: Callable[[str], Awaitable[str | None]] | None = None,
    webhook_lookup: Callable[[str], Awaitable[set[str]]] | None = None,
    sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, Any]:
    normalized = _validate(recipient, probe_id)
    send = sender or send_email_result
    provider_status = provider_lookup or _provider_last_event
    webhook_status = webhook_lookup or _webhook_events
    result = await send(
        to=normalized,
        subject="ForgeBase 商用寄送驗收（內部測試）",
        text_body=(
            "這是 ForgeBase 受控內部寄送驗收信。一般外部寄送與自動外聯開關仍維持關閉。"
        ),
        html_body=(
            "<p>這是 ForgeBase 受控內部寄送驗收信。</p>"
            "<p>一般外部寄送與自動外聯開關仍維持關閉。</p>"
        ),
        idempotency_key=f"forgebase-controlled-probe:{probe_id}",
        recipient_kind="internal",
        message_headers={"X-ForgeBase-Probe": probe_id},
        provider_override="resend",
    )
    if result.dry_run:
        raise ControlledProbeError("provider_send_was_dry_run")
    if not result.success or not result.delivered or not result.message_id:
        raise ControlledProbeError(result.error or "provider_acceptance_failed")

    last_event: str | None = None
    webhook_events: set[str] = set()
    for attempt in range(attempts):
        last_event, webhook_events = await asyncio.gather(
            provider_status(result.message_id),
            webhook_status(result.message_id),
        )
        provider_finished = last_event in SUCCESS_EVENTS | FAILURE_EVENTS
        webhook_finished = bool(webhook_events & (SUCCESS_EVENTS | FAILURE_EVENTS))
        if provider_finished and webhook_finished:
            break
        if attempt + 1 < attempts:
            await sleeper(interval_seconds)

    provider_delivered = last_event in SUCCESS_EVENTS
    webhook_delivered = bool(webhook_events & SUCCESS_EVENTS)
    passed = provider_delivered and webhook_delivered
    blockers = []
    if not provider_delivered:
        blockers.append("provider_delivery_not_confirmed")
    if not webhook_delivered:
        blockers.append("delivery_webhook_not_observed")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": "one_allowlisted_internal_delivery",
        "assessment": {
            "status": "passed" if passed else "failed",
            "provider_accepted": True,
            "provider_last_event": last_event or "not_observed",
            "provider_delivery_confirmed": provider_delivered,
            "webhook_events": sorted(webhook_events),
            "delivery_webhook_confirmed": webhook_delivered,
            "blockers": blockers,
        },
        "controls": {
            "recipient_exactly_internal_allowlisted": True,
            "recipient_matches_verified_sender": True,
            "external_delivery_switch_closed": True,
            "outreach_send_switch_closed": True,
            "automatic_outreach_used": False,
        },
        "evidence": {
            "provider_message_id_sha256": hashlib.sha256(
                result.message_id.encode("utf-8")
            ).hexdigest(),
        },
        "privacy": {
            "recipient_in_report": False,
            "provider_message_id_in_report": False,
            "credential_values_in_report": False,
            "message_body_in_report": False,
        },
    }


def _failure_report(reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operation": "one_allowlisted_internal_delivery",
        "assessment": {"status": "failed", "blockers": [reason[:100]]},
        "privacy": {
            "recipient_in_report": False,
            "provider_message_id_in_report": False,
            "credential_values_in_report": False,
            "message_body_in_report": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = asyncio.run(
            run_probe(
                recipient=os.environ.get("CONTROLLED_EMAIL_PROBE_RECIPIENT", ""),
                probe_id=os.environ.get("CONTROLLED_EMAIL_PROBE_ID", ""),
            )
        )
    except ControlledProbeError as exc:
        report = _failure_report(str(exc))
    except Exception:  # noqa: BLE001 -- report failures without leaking provider data
        report = _failure_report("unexpected_probe_failure")
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return 0 if report["assessment"]["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
