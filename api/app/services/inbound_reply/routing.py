"""Signed per-message Reply-To routing addresses."""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from email.utils import parseaddr

from app.core.config import settings

_LOCAL_RE = re.compile(r"^fb-([0-9a-f]{32})-([0-9a-f]{24})$")


def inbound_route_configured() -> bool:
    domain = settings.OUTREACH_INBOUND_DOMAIN.strip().lower().rstrip(".")
    secret = settings.OUTREACH_INBOUND_SECRET.strip()
    return bool(
        settings.INBOUND_REPLY_ENABLED
        and len(secret) >= 32
        and domain
        and "." in domain
        and "@" not in domain
        and "://" not in domain
        and len(domain) <= 253
    )


def _signature(message_id: uuid.UUID, tenant_id: uuid.UUID, email_digest: str) -> str:
    secret = settings.OUTREACH_INBOUND_SECRET.strip()
    if len(secret) < 32:
        raise ValueError("Inbound reply route signing is not configured")
    payload = f"{message_id.hex}:{tenant_id.hex}:{email_digest}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()[:24]


def issue_reply_to(
    *, message_id: uuid.UUID, tenant_id: uuid.UUID, email_digest: str
) -> tuple[str, str]:
    if not inbound_route_configured():
        raise ValueError("Inbound reply routing is not configured")
    local = f"fb-{message_id.hex}-{_signature(message_id, tenant_id, email_digest)}"
    address = f"{local}@{settings.OUTREACH_INBOUND_DOMAIN.strip().lower().rstrip('.')}"
    return address, hashlib.sha256(local.encode()).hexdigest()


def parse_reply_route(address: str) -> tuple[uuid.UUID, str] | None:
    parsed = parseaddr(str(address))[1].strip().lower()
    local, separator, domain = parsed.rpartition("@")
    expected_domain = settings.OUTREACH_INBOUND_DOMAIN.strip().lower().rstrip(".")
    if not separator or domain.rstrip(".") != expected_domain:
        return None
    match = _LOCAL_RE.fullmatch(local)
    if not match:
        return None
    return uuid.UUID(hex=match.group(1)), match.group(2)


def validate_reply_route(
    address: str, *, message_id: uuid.UUID, tenant_id: uuid.UUID, email_digest: str
) -> bool:
    parsed = parse_reply_route(address)
    if not parsed or parsed[0] != message_id:
        return False
    return hmac.compare_digest(
        parsed[1], _signature(message_id, tenant_id, email_digest)
    )


def route_hash(address: str) -> str:
    parsed = parseaddr(str(address))[1].strip().lower()
    local = parsed.rpartition("@")[0]
    return hashlib.sha256(local.encode()).hexdigest()
