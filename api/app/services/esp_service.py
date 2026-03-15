"""
2.4.3 Email Service Provider (ESP) 整合

Supports:
  1. Mailchimp (Audience / List management + Transactional via Mandrill)
  2. SendGrid (Contacts + Marketing Lists + Transactional)

Use cases:
  - Sync ForgeBase contacts to Mailchimp Audience or SendGrid List
  - Add/remove tags
  - Send transactional email via SendGrid if SENDGRID_API_KEY set

Required env vars (set only for the ESPs you use):
  MAILCHIMP_API_KEY       — e.g. "abc123-us1"
  MAILCHIMP_AUDIENCE_ID   — Mailchimp List/Audience ID
  SENDGRID_API_KEY        — SendGrid API key
  SENDGRID_LIST_ID        — SendGrid Marketing list ID
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mailchimp
# ---------------------------------------------------------------------------

def _mc_base() -> str:
    key = settings.MAILCHIMP_API_KEY
    if not key:
        return ""
    # Key format: "<key>-<dc>"
    dc = key.split("-")[-1] if "-" in key else "us1"
    return f"https://{dc}.api.mailchimp.com/3.0"


def _mc_auth() -> dict:
    return {"Authorization": f"Basic _:{settings.MAILCHIMP_API_KEY}"}


async def mailchimp_upsert_member(
    email: str,
    first_name: str = "",
    last_name: str = "",
    tags: Optional[list[str]] = None,
    status: str = "subscribed",  # "subscribed" | "pending" | "unsubscribed"
) -> dict:
    """Upsert a subscriber in the Mailchimp Audience."""
    base = _mc_base()
    if not base or not settings.MAILCHIMP_AUDIENCE_ID:
        logger.warning("Mailchimp not configured — skipping upsert for %s", email)
        return {"skipped": True}

    import hashlib
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    url = f"{base}/lists/{settings.MAILCHIMP_AUDIENCE_ID}/members/{email_hash}"
    body: dict = {
        "email_address": email,
        "status_if_new": status,
        "merge_fields": {"FNAME": first_name, "LNAME": last_name},
    }
    if tags:
        body["tags"] = [{"name": t, "status": "active"} for t in tags]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.put(url, auth=("_", settings.MAILCHIMP_API_KEY), json=body)
            if res.status_code in (200, 201):
                return res.json()
            logger.error("Mailchimp upsert error %s: %s", res.status_code, res.text[:200])
            return {"error": res.text[:200]}
    except Exception as exc:  # noqa: BLE001
        logger.error("Mailchimp upsert exception: %s", exc)
        return {"error": str(exc)}


async def mailchimp_add_tags(email: str, tags: list[str]) -> bool:
    """Add tags to a Mailchimp subscriber."""
    base = _mc_base()
    if not base or not settings.MAILCHIMP_AUDIENCE_ID:
        return False

    import hashlib
    email_hash = hashlib.md5(email.lower().encode()).hexdigest()
    url = f"{base}/lists/{settings.MAILCHIMP_AUDIENCE_ID}/members/{email_hash}/tags"
    body = {"tags": [{"name": t, "status": "active"} for t in tags]}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(url, auth=("_", settings.MAILCHIMP_API_KEY), json=body)
            return res.status_code in (200, 201, 204)
    except Exception as exc:  # noqa: BLE001
        logger.error("Mailchimp add_tags exception: %s", exc)
        return False


async def mailchimp_get_audience_stats() -> dict:
    """Get basic stats for the Mailchimp Audience."""
    base = _mc_base()
    if not base or not settings.MAILCHIMP_AUDIENCE_ID:
        return {}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                f"{base}/lists/{settings.MAILCHIMP_AUDIENCE_ID}",
                auth=("_", settings.MAILCHIMP_API_KEY),
            )
            if res.status_code == 200:
                d = res.json()
                return {
                    "member_count": d.get("stats", {}).get("member_count"),
                    "unsubscribe_count": d.get("stats", {}).get("unsubscribe_count"),
                    "campaign_last_sent": d.get("campaign_last_sent"),
                }
    except Exception as exc:  # noqa: BLE001
        logger.error("Mailchimp stats exception: %s", exc)
    return {}


# ---------------------------------------------------------------------------
# SendGrid
# ---------------------------------------------------------------------------

SG_API = "https://api.sendgrid.com/v3"


def _sg_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }


async def sendgrid_upsert_contact(
    email: str,
    first_name: str = "",
    last_name: str = "",
    list_ids: Optional[list[str]] = None,
    custom_fields: Optional[dict] = None,
) -> dict:
    """Add/update a contact in SendGrid Marketing and optionally add to list(s)."""
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not configured — skipping contact upsert for %s", email)
        return {"skipped": True}

    contact: dict = {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
    }
    if custom_fields:
        contact["custom_fields"] = custom_fields

    body: dict = {"contacts": [contact]}
    if list_ids:
        body["list_ids"] = list_ids
    elif settings.SENDGRID_LIST_ID:
        body["list_ids"] = [settings.SENDGRID_LIST_ID]

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.put(
                f"{SG_API}/marketing/contacts",
                headers=_sg_headers(),
                json=body,
            )
            if res.status_code in (200, 201, 202):
                return res.json() if res.content else {"success": True}
            logger.error("SendGrid upsert error %s: %s", res.status_code, res.text[:200])
            return {"error": res.text[:200]}
    except Exception as exc:  # noqa: BLE001
        logger.error("SendGrid upsert exception: %s", exc)
        return {"error": str(exc)}


async def sendgrid_send_email(
    to: str,
    subject: str,
    html_body: Optional[str] = None,
    text_body: Optional[str] = None,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> bool:
    """Send transactional email via SendGrid."""
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not configured — skipping send to %s", to)
        return False

    sender = from_email or settings.EMAIL_FROM
    sender_name = from_name or settings.EMAIL_FROM_NAME

    body: dict = {
        "personalizations": [{"to": [{"email": to}]}],
        "from": {"email": sender, "name": sender_name},
        "subject": subject,
        "content": [],
    }
    if text_body:
        body["content"].append({"type": "text/plain", "value": text_body})
    if html_body:
        body["content"].append({"type": "text/html", "value": html_body})
    if not body["content"]:
        body["content"].append({"type": "text/plain", "value": subject})

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                f"{SG_API}/mail/send",
                headers=_sg_headers(),
                json=body,
            )
            return res.status_code in (200, 201, 202)
    except Exception as exc:  # noqa: BLE001
        logger.error("SendGrid send exception: %s", exc)
        return False


async def sendgrid_get_stats() -> dict:
    """Get basic SendGrid list stats."""
    if not settings.SENDGRID_API_KEY or not settings.SENDGRID_LIST_ID:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(
                f"{SG_API}/marketing/lists/{settings.SENDGRID_LIST_ID}?contact_count=true",
                headers=_sg_headers(),
            )
            if res.status_code == 200:
                d = res.json()
                return {"contact_count": d.get("contact_count"), "name": d.get("name")}
    except Exception as exc:  # noqa: BLE001
        logger.error("SendGrid get_stats exception: %s", exc)
    return {}
