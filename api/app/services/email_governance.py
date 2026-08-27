from __future__ import annotations

import hashlib
import hmac
from typing import Literal, Optional

from sqlmodel import select

from app.core.config import settings
from app.db.session import get_session_ctx
from app.models.email_delivery import EmailSuppression

RecipientKind = Literal["external", "internal", "test"]


def normalize_email(address: str) -> str:
    return address.strip().lower()


def email_hash(address: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        normalize_email(address).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def mask_email(address: str) -> str:
    normalized = normalize_email(address)
    local, separator, domain = normalized.partition("@")
    if not separator:
        return "***"
    visible = local[:1]
    return f"{visible}***@{domain}"


def _allowlist(raw: str) -> set[str]:
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def address_allowed(address: str, raw_allowlist: str) -> bool:
    normalized = normalize_email(address)
    _, _, domain = normalized.partition("@")
    allowed = _allowlist(raw_allowlist)
    return normalized in allowed or domain in allowed


def delivery_policy_error(address: str, recipient_kind: RecipientKind) -> Optional[str]:
    if recipient_kind == "external" and not settings.EMAIL_EXTERNAL_DELIVERY_ENABLED:
        return "external_delivery_disabled"
    if recipient_kind == "internal" and not address_allowed(
        address, settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST
    ):
        return "internal_recipient_not_allowlisted"
    return None


async def is_suppressed(address: str) -> bool:
    digest = email_hash(address)
    async with get_session_ctx() as db:
        row = (
            await db.exec(
                select(EmailSuppression.id).where(
                    EmailSuppression.scope_key == "global",
                    EmailSuppression.email_hash == digest,
                    EmailSuppression.active.is_(True),
                )
            )
        ).first()
    return row is not None


def is_authorized_synthetic_request(token: Optional[str]) -> bool:
    configured = settings.SYNTHETIC_TEST_TOKEN
    return bool(configured and token and hmac.compare_digest(configured, token))
