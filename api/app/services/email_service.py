"""
Email Service — send transactional/nurture emails.
2.1.4 Email Nurture Engine.
Resend is the single supported delivery provider.
"""

import logging
import re
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.services.email_governance import (
    RecipientKind,
    delivery_policy_error,
    is_suppressed,
)

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
_HEADER_NAME = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")


def _clean_message_headers(headers: dict[str, str] | None) -> dict[str, str]:
    """Reject header injection and provider-owned transport headers."""
    cleaned: dict[str, str] = {}
    for raw_name, raw_value in (headers or {}).items():
        name = str(raw_name).strip()
        value = str(raw_value).strip()
        if (
            not name
            or not _HEADER_NAME.fullmatch(name)
            or "\r" in value
            or "\n" in value
            or len(name) > 100
            or len(value) > 2000
            or name.lower()
            in {"from", "to", "subject", "authorization", "content-type"}
        ):
            raise ValueError("Invalid custom email header")
        cleaned[name] = value
    return cleaned


@dataclass(frozen=True)
class EmailDeliveryResult:
    """Outcome of one email attempt, keeping dry runs separate from delivery."""

    success: bool
    delivered: bool
    dry_run: bool
    provider: str
    message_id: str | None = None
    error: str | None = None


async def _send_via_resend(
    to: str,
    subject: str,
    html_body: str | None,
    text_body: str | None,
    from_field: str,
    idempotency_key: str | None = None,
    message_headers: dict[str, str] | None = None,
    reply_to: str | None = None,
) -> EmailDeliveryResult:
    """Send email through Resend."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping send to %s", to)
        return EmailDeliveryResult(
            False, False, False, "resend", error="missing_api_key"
        )

    payload: dict = {"from": from_field, "to": [to], "subject": subject}
    if html_body:
        payload["html"] = html_body
    if text_body:
        payload["text"] = text_body
    if not html_body and not text_body:
        payload["text"] = subject
    cleaned_headers = _clean_message_headers(message_headers)
    if cleaned_headers:
        payload["headers"] = cleaned_headers
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "ForgeBase/1.0",
            }
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key[:256]
            r = await client.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
            )
            if r.status_code in (200, 201):
                message_id = None
                try:
                    message_id = r.json().get("id")
                except ValueError:
                    pass
                return EmailDeliveryResult(
                    True, True, False, "resend", message_id=message_id
                )
            logger.error("Resend API error %s: %s", r.status_code, r.text[:200])
            return EmailDeliveryResult(
                False, False, False, "resend", error=f"http_{r.status_code}"
            )
    except httpx.RequestError:
        logger.exception("Resend send request failed to %s", to)
        return EmailDeliveryResult(
            False, False, False, "resend", error="request_failed"
        )
    except Exception:
        logger.exception("Unexpected Resend send failure to %s", to)
        return EmailDeliveryResult(
            False, False, False, "resend", error="unexpected_failure"
        )


async def send_email_result(
    to: str,
    subject: str,
    html_body: str | None = None,
    text_body: str | None = None,
    from_name: str | None = None,
    from_email: str | None = None,
    idempotency_key: str | None = None,
    recipient_kind: RecipientKind = "external",
    message_headers: dict[str, str] | None = None,
    provider_override: str | None = None,
    reply_to: str | None = None,
) -> EmailDeliveryResult:
    """Send an email and report whether it was simulated or provider-accepted."""
    sender_name = from_name or settings.EMAIL_FROM_NAME
    sender_addr = from_email or settings.EMAIL_FROM
    provider = (provider_override or "resend").lower()
    if provider != "resend":
        return EmailDeliveryResult(
            False, False, False, provider, error="unsupported_provider"
        )
    has_key = bool(settings.RESEND_API_KEY)

    if settings.EMAIL_DRY_RUN:
        logger.info(
            "EMAIL_DRY_RUN to=%s subject=%s provider=%s configured=%s",
            to,
            subject,
            provider,
            has_key,
        )
        return EmailDeliveryResult(True, False, True, provider)

    policy_error = delivery_policy_error(to, recipient_kind)
    if policy_error:
        logger.warning(
            "Email blocked by platform policy recipient_kind=%s reason=%s",
            recipient_kind,
            policy_error,
        )
        return EmailDeliveryResult(False, False, False, provider, error=policy_error)

    try:
        if recipient_kind != "test" and await is_suppressed(to):
            logger.warning(
                "Email blocked by suppression list recipient_kind=%s", recipient_kind
            )
            return EmailDeliveryResult(
                False, False, False, provider, error="recipient_suppressed"
            )
    except Exception:
        # Delivery governance fails closed: a database outage must not bypass a
        # complaint/bounce suppression decision.
        logger.exception("Suppression lookup failed; blocking delivery")
        return EmailDeliveryResult(
            False, False, False, provider, error="suppression_check_failed"
        )

    if not has_key:
        logger.error("Email provider is not configured: provider=%s", provider)
        return EmailDeliveryResult(
            False, False, False, provider, error="missing_api_key"
        )

    from_field = f"{sender_name} <{sender_addr}>"
    return await _send_via_resend(
        to,
        subject,
        html_body,
        text_body,
        from_field,
        idempotency_key,
        message_headers,
        reply_to,
    )


async def send_email(
    to: str,
    subject: str,
    html_body: str | None = None,
    text_body: str | None = None,
    from_name: str | None = None,
    from_email: str | None = None,
    idempotency_key: str | None = None,
    recipient_kind: RecipientKind = "external",
    message_headers: dict[str, str] | None = None,
    provider_override: str | None = None,
    reply_to: str | None = None,
) -> bool:
    """
    Send a single transactional email.
    Delivers through Resend.
    """
    result = await send_email_result(
        to=to,
        subject=subject,
        html_body=html_body,
        text_body=text_body,
        from_name=from_name,
        from_email=from_email,
        idempotency_key=idempotency_key,
        recipient_kind=recipient_kind,
        message_headers=message_headers,
        provider_override=provider_override,
        reply_to=reply_to,
    )
    return result.success


async def send_nurture_step(contact, step) -> bool:
    """Send one nurture sequence step email to a contact."""
    result = await send_nurture_step_result(contact, step)
    return result.success


async def send_nurture_step_result(
    contact,
    step,
    *,
    idempotency_key: str | None = None,
) -> EmailDeliveryResult:
    """Send a nurture step while preserving its provider delivery outcome."""
    return await send_email_result(
        to=contact.email,
        subject=step.subject,
        html_body=step.html_body,
        text_body=step.text_body,
        from_name=step.from_name,
        from_email=step.from_email,
        idempotency_key=idempotency_key or f"nurture-{step.id}-{contact.id}",
        recipient_kind="external",
    )
