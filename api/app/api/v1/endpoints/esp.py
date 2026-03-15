"""
2.4.3 ESP 整合 API endpoints

Routes (prefix: /esp, mounted on tracking_router → /api/v1/tracking/esp/):
  GET  /status                    — active provider + configured ESPs
  POST /test-email                — send test email via active provider
  POST /mailchimp/sync-contacts   — bulk sync all contacts to Mailchimp Audience
  GET  /mailchimp/stats           — Mailchimp Audience stats
  GET  /sendgrid/stats            — SendGrid list stats
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlmodel import select

from app.api.v1.deps import require_admin as get_current_admin
from app.db.session import get_session
from app.core.config import settings
from app.models.contact import Contact
from app.services import email_service
from app.services.esp_service import (
    mailchimp_add_tags,
    mailchimp_get_audience_stats,
    mailchimp_upsert_member,
    sendgrid_get_stats,
    sendgrid_upsert_contact,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/esp", tags=["esp"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TestEmailIn(BaseModel):
    to: EmailStr
    subject: str = "ForgeBase 測試信件"
    body: Optional[str] = None


class SyncContactsResult(BaseModel):
    total: int
    success: int
    failed: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/status")
async def get_esp_status(_admin=Depends(get_current_admin)):
    """Return which ESPs are configured and the active transactional provider."""
    return {
        "active_provider": settings.ESP_PROVIDER,
        "resend_configured": bool(settings.RESEND_API_KEY),
        "sendgrid_configured": bool(settings.SENDGRID_API_KEY),
        "mailchimp_configured": bool(settings.MAILCHIMP_API_KEY and settings.MAILCHIMP_AUDIENCE_ID),
    }


@router.post("/test-email")
async def send_test_email(
    payload: TestEmailIn,
    _admin=Depends(get_current_admin),
):
    """Send a test email through the currently active ESP provider."""
    html_body = f"<p>{payload.body or '這是一封來自 ForgeBase 的測試信件。'}</p>"
    ok = await email_service.send_email(
        to=str(payload.to),
        subject=payload.subject,
        html_body=html_body,
        text_body=payload.body or "這是一封來自 ForgeBase 的測試信件。",
    )
    if not ok:
        raise HTTPException(status_code=502, detail="Email send failed — check provider credentials.")
    return {"success": True, "provider": settings.ESP_PROVIDER, "to": payload.to}


@router.post("/mailchimp/sync-contacts", response_model=SyncContactsResult)
async def sync_contacts_to_mailchimp(
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    """
    Bulk-upsert all active ForgeBase contacts into the Mailchimp Audience.
    Runs synchronously (for large lists, consider moving to a background task).
    """
    if not settings.MAILCHIMP_API_KEY or not settings.MAILCHIMP_AUDIENCE_ID:
        raise HTTPException(status_code=400, detail="Mailchimp not configured: set MAILCHIMP_API_KEY and MAILCHIMP_AUDIENCE_ID.")

    contacts = (await db.execute(select(Contact))).scalars().all()

    success = 0
    failed = 0
    for contact in contacts:
        tags = []
        if contact.lifecycle_stage:
            tags.append(contact.lifecycle_stage)
        if contact.company_name:
            tags.append(f"company:{contact.company_name}")

        full_name: str = contact.full_name or ""
        parts = full_name.split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""

        result = await mailchimp_upsert_member(
            email=contact.email,
            first_name=first_name,
            last_name=last_name,
            tags=tags,
        )
        if "error" in result or result.get("skipped"):
            failed += 1
        else:
            success += 1

        # Small delay to avoid Mailchimp rate limits
        await asyncio.sleep(0.05)

    return SyncContactsResult(total=len(contacts), success=success, failed=failed)


@router.post("/sendgrid/sync-contacts", response_model=SyncContactsResult)
async def sync_contacts_to_sendgrid(
    db=Depends(get_session),
    _admin=Depends(get_current_admin),
):
    """
    Bulk-upsert all active ForgeBase contacts into the SendGrid Marketing contact list.
    SendGrid accepts up to 30,000 contacts per request, so this chunks automatically.
    """
    if not settings.SENDGRID_API_KEY:
        raise HTTPException(status_code=400, detail="SendGrid not configured: set SENDGRID_API_KEY.")

    contacts = (await db.execute(select(Contact))).scalars().all()

    success = 0
    failed = 0
    # SendGrid /marketing/contacts accepts batch upserts; we process individually for error tracking
    for contact in contacts:
        full_name: str = contact.full_name or ""
        parts = full_name.split(" ", 1)
        result = await sendgrid_upsert_contact(
            email=contact.email,
            first_name=parts[0] if parts else "",
            last_name=parts[1] if len(parts) > 1 else "",
        )
        if "error" in result or result.get("skipped"):
            failed += 1
        else:
            success += 1

        await asyncio.sleep(0.05)

    return SyncContactsResult(total=len(contacts), success=success, failed=failed)


@router.get("/mailchimp/stats")
async def get_mailchimp_stats(_admin=Depends(get_current_admin)):
    if not settings.MAILCHIMP_API_KEY:
        raise HTTPException(status_code=400, detail="Mailchimp not configured.")
    stats = await mailchimp_get_audience_stats()
    return stats


@router.get("/sendgrid/stats")
async def get_sendgrid_stats(_admin=Depends(get_current_admin)):
    if not settings.SENDGRID_API_KEY:
        raise HTTPException(status_code=400, detail="SendGrid not configured.")
    stats = await sendgrid_get_stats()
    return stats
