"""Signed, privacy-minimised one-click unsubscribe tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass

from app.core.config import settings


class InvalidUnsubscribeToken(ValueError):
    pass


@dataclass(frozen=True)
class UnsubscribeClaims:
    message_id: uuid.UUID
    tenant_id: uuid.UUID
    email_hash: str
    scope: str
    expires_at: int


def _secret() -> bytes:
    value = settings.OUTREACH_UNSUBSCRIBE_SECRET.strip()
    if len(value) < 32:
        raise InvalidUnsubscribeToken("Unsubscribe signing is not configured")
    return value.encode()


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_unsubscribe_token(
    *, message_id: uuid.UUID, tenant_id: uuid.UUID, email_hash: str, scope: str
) -> str:
    if scope not in {"tenant", "global"}:
        raise InvalidUnsubscribeToken("Invalid unsubscribe scope")
    payload = {
        "v": 1,
        "mid": str(message_id),
        "tid": str(tenant_id),
        "eh": email_hash,
        "scope": scope,
        "exp": int(time.time()) + settings.OUTREACH_UNSUBSCRIBE_TOKEN_DAYS * 86400,
    }
    encoded = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    )
    signature = _encode(hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_unsubscribe_token(token: str) -> UnsubscribeClaims:
    try:
        encoded, supplied = token.split(".", 1)
        expected = _encode(
            hmac.new(_secret(), encoded.encode(), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(supplied, expected):
            raise InvalidUnsubscribeToken("Invalid unsubscribe token")
        payload = json.loads(_decode(encoded))
        if payload.get("v") != 1 or int(payload["exp"]) < int(time.time()):
            raise InvalidUnsubscribeToken("Unsubscribe token expired")
        email_digest = str(payload["eh"])
        scope = str(payload["scope"])
        if len(email_digest) != 64 or scope not in {"tenant", "global"}:
            raise InvalidUnsubscribeToken("Invalid unsubscribe token")
        return UnsubscribeClaims(
            message_id=uuid.UUID(str(payload["mid"])),
            tenant_id=uuid.UUID(str(payload["tid"])),
            email_hash=email_digest,
            scope=scope,
            expires_at=int(payload["exp"]),
        )
    except InvalidUnsubscribeToken:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise InvalidUnsubscribeToken("Invalid unsubscribe token") from exc
