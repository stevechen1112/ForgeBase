"""Short-lived, tenant-bound form challenges and optional Turnstile checks."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from typing import Optional

import httpx

from app.core.config import settings


def issue_form_challenge(tenant_id: object | None) -> str:
    payload = {
        "iat": int(time.time()),
        "tenant": str(tenant_id or "public"),
        "nonce": secrets.token_urlsafe(12),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    body = base64.urlsafe_b64encode(raw).rstrip(b"=")
    signature = hmac.new(settings.SECRET_KEY.encode(), body, hashlib.sha256).digest()
    return f"{body.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def validate_form_challenge(token: str, tenant_id: object | None) -> bool:
    try:
        body_text, signature_text = token.split(".", 1)
        body = body_text.encode()
        expected = hmac.new(settings.SECRET_KEY.encode(), body, hashlib.sha256).digest()
        supplied = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
        if not hmac.compare_digest(expected, supplied):
            return False
        raw = base64.urlsafe_b64decode(body_text + "=" * (-len(body_text) % 4))
        payload = json.loads(raw)
        age = int(time.time()) - int(payload["iat"])
        return (
            str(payload.get("tenant")) == str(tenant_id or "public")
            and settings.RFQ_CHALLENGE_MIN_AGE_SECONDS <= age <= settings.RFQ_CHALLENGE_MAX_AGE_SECONDS
        )
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False


async def verify_turnstile(
    token: Optional[str],
    remote_ip: Optional[str],
    *,
    expected_action: Optional[str] = None,
) -> bool:
    """Fail closed only when the operator explicitly configured Turnstile."""
    if not settings.TURNSTILE_SECRET_KEY:
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                data={
                    "secret": settings.TURNSTILE_SECRET_KEY,
                    "response": token,
                    "remoteip": remote_ip or "",
                    "idempotency_key": str(uuid.uuid4()),
                },
            )
        response.raise_for_status()
        result = response.json()
        if not result.get("success"):
            return False
        allowed_hosts = {
            item.strip().lower()
            for item in settings.TURNSTILE_ALLOWED_HOSTNAMES.split(",")
            if item.strip()
        }
        hostname = str(result.get("hostname") or "").strip().lower()
        if allowed_hosts and hostname not in allowed_hosts:
            return False
        required_action = (
            expected_action
            if expected_action is not None
            else settings.TURNSTILE_EXPECTED_ACTION.strip()
        )
        if required_action and result.get("action") != required_action:
            return False
        return True
    except (httpx.HTTPError, ValueError):
        return False
