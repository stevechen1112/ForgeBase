from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Iterable

from app.core.config import settings


def resend_webhook_signing_configured() -> bool:
    """Return whether the configured Svix secret can safely verify webhooks."""
    secret = settings.RESEND_WEBHOOK_SECRET.strip().removeprefix("whsec_")
    if not secret:
        return False
    try:
        return len(base64.b64decode(secret, validate=True)) >= 16
    except (ValueError, binascii.Error):
        return False


def verify_resend_signature(raw_body: bytes, headers: dict[str, str]) -> bool:
    """Verify Resend/Svix signature using the untouched request body."""
    secret = settings.RESEND_WEBHOOK_SECRET.strip()
    message_id = headers.get("svix-id", "")
    timestamp = headers.get("svix-timestamp", "")
    signature_header = headers.get("svix-signature", "")
    if (
        not resend_webhook_signing_configured()
        or not message_id
        or not timestamp
        or not signature_header
    ):
        return False
    try:
        ts = int(timestamp)
        if abs(int(time.time()) - ts) > settings.RESEND_WEBHOOK_TOLERANCE_SECONDS:
            return False
        encoded_secret = secret.removeprefix("whsec_")
        key = base64.b64decode(encoded_secret, validate=True)
        signed = f"{message_id}.{timestamp}.".encode("utf-8") + raw_body
        expected = base64.b64encode(
            hmac.new(key, signed, hashlib.sha256).digest()
        ).decode()
        signatures = []
        for part in signature_header.split():
            version, separator, value = part.partition(",")
            if separator and version == "v1":
                signatures.append(value)
        return any(hmac.compare_digest(expected, candidate) for candidate in signatures)
    except (ValueError, TypeError, binascii.Error):
        return False


def parse_occurred_at(payload: dict[str, Any]) -> datetime | None:
    value = payload.get("created_at") or (payload.get("data") or {}).get("created_at")
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return None


def recipient_addresses(payload: dict[str, Any]) -> list[str]:
    data = payload.get("data") or {}
    values: Iterable[Any]
    direct = data.get("email")
    if direct:
        values = [direct]
    else:
        to_value = data.get("to") or []
        values = to_value if isinstance(to_value, list) else [to_value]
    result: list[str] = []
    for value in values:
        address = str(value).strip().lower()
        if "@" in address and address not in result:
            result.append(address)
    return result


def provider_message_id(payload: dict[str, Any]) -> str | None:
    value = (payload.get("data") or {}).get("email_id")
    return str(value)[:120] if value else None


def decode_payload(raw_body: bytes) -> dict[str, Any]:
    value = json.loads(raw_body)
    if not isinstance(value, dict):
        raise ValueError("Webhook payload must be an object")
    return value
