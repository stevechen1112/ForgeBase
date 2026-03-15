"""
Webhook Service — 1b.5.3

Sends outbound webhook events to configured endpoints (spec 12.8.4).

Supported events:
  rfq.created                  — new RFQ submitted
  rfq.status_changed           — RFQ status updated
  contact.created              — new contact form submission
  contact.intent_stage_changed — visitor stage escalation (linked contact)
  visitor.became_hot           — visitor entered hot / sales_ready stage

Security:
  HMAC-SHA256 signature in X-Webhook-Signature header (sha256=<hex>).

Retry schedule (3 total attempts):
  Attempt 0 — immediate
  Attempt 1 — after 60 s
  Attempt 2 — after 300 s

Env vars:
  WEBHOOK_ENDPOINT_URLS  — comma-separated list of endpoint URLs
  WEBHOOK_SECRET         — signing secret (leave empty to disable signing)
"""
import asyncio
import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_WEBHOOK_ENDPOINT_URLS = os.getenv("WEBHOOK_ENDPOINT_URLS", "")
_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

_RETRY_DELAYS = [0, 60, 300]  # seconds between attempts


def _endpoints() -> list[str]:
    return [u.strip() for u in _WEBHOOK_ENDPOINT_URLS.split(",") if u.strip()]


def _sign(payload_bytes: bytes) -> str:
    """Return HMAC-SHA256 hex signature of the raw payload bytes."""
    return hmac.digest(
        _WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256
    ).hex()


def fire_webhook(event_type: str, data: dict[str, Any]) -> None:
    """
    Schedule webhook delivery to all configured endpoints (non-blocking).
    Must be called from an active asyncio event loop (i.e. inside a FastAPI handler).
    """
    endpoints = _endpoints()
    if not endpoints:
        return

    webhook_id = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "metadata": {
            "webhook_id": webhook_id,
            "retry_count": 0,
        },
    }

    for url in endpoints:
        asyncio.create_task(_send_with_retry(url, event_type, payload.copy()))


async def _send_with_retry(url: str, event_type: str, payload: dict) -> None:
    """Attempt delivery up to 3 times with exponential back-off."""
    for attempt, delay in enumerate(_RETRY_DELAYS):
        if delay:
            await asyncio.sleep(delay)

        payload["metadata"]["retry_count"] = attempt
        body_bytes = json.dumps(payload, ensure_ascii=False, default=str).encode()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-Id": payload["metadata"]["webhook_id"],
        }
        if _WEBHOOK_SECRET:
            headers["X-Webhook-Signature"] = f"sha256={_sign(body_bytes)}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, content=body_bytes, headers=headers)
            if resp.status_code < 400:
                logger.info(
                    "webhook.sent event=%s url=%s status=%d attempt=%d",
                    event_type, url, resp.status_code, attempt,
                )
                return
            logger.warning(
                "webhook.error event=%s url=%s attempt=%d status=%d",
                event_type, url, attempt, resp.status_code,
            )
        except Exception as exc:
            logger.warning(
                "webhook.exception event=%s url=%s attempt=%d error=%s",
                event_type, url, attempt, exc,
            )

    logger.error(
        "webhook.failed event=%s url=%s all_attempts_exhausted", event_type, url
    )
