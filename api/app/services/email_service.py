"""
Email Service — send transactional/nurture emails.
2.1.4 Email Nurture Engine.
2.4.3 Multi-ESP support: routes to Resend or SendGrid based on ESP_PROVIDER setting.
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def _send_via_resend(
    to: str,
    subject: str,
    html_body: Optional[str],
    text_body: Optional[str],
    from_field: str,
) -> bool:
    """Send email through Resend."""
    if not settings.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set — skipping send to %s", to)
        return False

    payload: dict = {"from": from_field, "to": [to], "subject": subject}
    if html_body:
        payload["html"] = html_body
    if text_body:
        payload["text"] = text_body
    if not html_body and not text_body:
        payload["text"] = subject

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                RESEND_API_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if r.status_code in (200, 201):
                return True
            logger.error("Resend API error %s: %s", r.status_code, r.text[:200])
            return False
    except httpx.RequestError:
        logger.exception("Resend send request failed to %s", to)
        return False
    except Exception:
        logger.exception("Unexpected Resend send failure to %s", to)
        return False


async def _send_via_sendgrid(
    to: str,
    subject: str,
    html_body: Optional[str],
    text_body: Optional[str],
    from_email: str,
    from_name: str,
) -> bool:
    """Send email through SendGrid."""
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — skipping send to %s", to)
        return False

    content = []
    if text_body:
        content.append({"type": "text/plain", "value": text_body})
    if html_body:
        content.append({"type": "text/html", "value": html_body})
    if not content:
        content.append({"type": "text/plain", "value": subject})

    body = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": from_email, "name": from_name},
        "subject": subject,
        "content": content,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=body,
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if r.status_code in (200, 201, 202):
                return True
            logger.error("SendGrid API error %s: %s", r.status_code, r.text[:200])
            return False
    except httpx.RequestError:
        logger.exception("SendGrid send request failed to %s", to)
        return False
    except Exception:
        logger.exception("Unexpected SendGrid send failure to %s", to)
        return False


async def send_email(
    to: str,
    subject: str,
    html_body: Optional[str] = None,
    text_body: Optional[str] = None,
    from_name: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """
    Send a single transactional email.
    Routes to the active ESP provider defined by settings.ESP_PROVIDER.
    """
    sender_name = from_name or settings.EMAIL_FROM_NAME
    sender_addr = from_email or settings.EMAIL_FROM

    provider = (settings.ESP_PROVIDER or "resend").lower()
    has_key = bool(settings.SENDGRID_API_KEY) if provider == "sendgrid" else bool(settings.RESEND_API_KEY)
    if settings.EMAIL_DRY_RUN or not has_key:
        logger.info(
            "EMAIL_DRY_RUN send to=%s subject=%s provider=%s has_key=%s",
            to,
            subject,
            provider,
            has_key,
        )
        return True

    if provider == "sendgrid":
        return await _send_via_sendgrid(to, subject, html_body, text_body, sender_addr, sender_name)

    # Default: Resend
    from_field = f"{sender_name} <{sender_addr}>"
    return await _send_via_resend(to, subject, html_body, text_body, from_field)


async def send_nurture_step(contact, step) -> bool:
    """Send one nurture sequence step email to a contact."""
    return await send_email(
        to=contact.email,
        subject=step.subject,
        html_body=step.html_body,
        text_body=step.text_body,
        from_name=step.from_name,
        from_email=step.from_email,
    )


