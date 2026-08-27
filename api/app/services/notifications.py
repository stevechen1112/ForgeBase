"""
Notification Service — 1b.4.7

Sends internal email notifications through the shared ESP service.

Triggers:
  - notify_new_rfq(rfq_id)         — alert sales team of new RFQ
  - notify_rfq_assigned(rfq_id)    — notify assigned user
  - notify_rfq_reminder(rfq_id)    — 24-hour unacknowledged reminder
  - notify_rfq_escalation(rfq_id)  — 48-hour escalation to manager

Configuration via env vars:
  ESP_PROVIDER / RESEND_API_KEY / EMAIL_FROM / EMAIL_FROM_NAME
  SALES_NOTIFY_EMAIL — fallback "all new RFQs" internal recipient
  MANAGER_EMAIL      — escalation recipient
"""
import html
import logging
import uuid
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.contact import Contact
from app.models.rfq_request import RFQRequest
from app.models.tenant import Tenant
from app.models.user import User
from app.models.visitor import Visitor
from app.services.email_service import EmailDeliveryResult, send_email_result
from app.services.capability_access import tenant_has_feature

logger = logging.getLogger(__name__)

async def _send_email(
    to: str,
    subject: str,
    body_html: str,
    *,
    idempotency_key: str,
) -> EmailDeliveryResult:
    """Send through the configured ESP; never treat a dry run as delivered."""
    if not to:
        return EmailDeliveryResult(
            False,
            False,
            settings.EMAIL_DRY_RUN,
            settings.ESP_PROVIDER,
            error="empty_recipient",
        )
    return await send_email_result(
        to=to,
        subject=subject,
        html_body=body_html,
        idempotency_key=idempotency_key,
        recipient_kind="internal",
    )


async def notify_visitor_hot(visitor_id: uuid.UUID, stage: str, score: int) -> None:
    """
    Alert sales team when an anonymous visitor reaches hot/sales_ready
    without having submitted an RFQ. (1b.3.5 Intent trigger)
    """
    if not settings.SALES_NOTIFY_EMAIL:
        return
    try:
        async with get_session_ctx() as db:
            visitor = await db.get(Visitor, visitor_id)
            if not visitor or not visitor.tenant_id:
                return
            tenant = await db.get(Tenant, visitor.tenant_id)
            if (
                not tenant
                or not tenant_has_feature(tenant, "notifications")
                or not tenant_has_feature(tenant, "intent_scoring")
            ):
                return
            contact_name = "Anonymous"
            contact_email = "—"
            if visitor and visitor.contact_id:
                contact = await db.get(Contact, visitor.contact_id)
                if contact:
                    contact_name = contact.full_name
                    contact_email = contact.email
            stage_label = stage.replace("_", " ").title()
            contact_name = html.escape(contact_name or "Anonymous", quote=True)
            contact_email = html.escape(contact_email or "—", quote=True)
            stage_label = html.escape(stage_label, quote=True)
            admin_url = settings.ADMIN_URL.rstrip("/")
            subject = f"[ForgeBase] 🔥 High-Intent Visitor — Stage: {stage_label} (score {score})"
            body = f"""
<html><body style="font-family:Arial,sans-serif;color:#333">
<h2 style="color:#1a56db">ForgeBase — High-Intent Visitor Alert</h2>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:8px;font-weight:bold;width:180px">Visitor ID</td><td style="padding:8px">{visitor_id}</td></tr>
  <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold">Intent Stage</td><td style="padding:8px">{stage_label}</td></tr>
  <tr><td style="padding:8px;font-weight:bold">Intent Score</td><td style="padding:8px">{score}</td></tr>
  <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold">Known As</td><td style="padding:8px">{contact_name} ({contact_email})</td></tr>
</table>
<p style="margin-top:20px">
  <a href="{admin_url}/dashboard/visitors/{visitor_id}"
     style="background:#1a56db;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px">
    View Visitor Profile
  </a>
</p>
</body></html>
"""
            await _send_email(
                settings.SALES_NOTIFY_EMAIL,
                subject,
                body,
                idempotency_key=f"visitor-hot-{visitor_id}-{stage}-{score}",
            )
    except SQLAlchemyError:
        logger.exception("notify_visitor_hot database error visitor_id=%s", visitor_id)
    except Exception:
        logger.exception("notify_visitor_hot unexpected error visitor_id=%s", visitor_id)


# ── Notification triggers ─────────────────────────────────────────────────────

async def notify_new_rfq(rfq_id: uuid.UUID) -> bool:
    """Alert the configured sales inbox about a new RFQ."""
    if not settings.SALES_NOTIFY_EMAIL:
        return False
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq:
                return False
            subject = f"[ForgeBase] New RFQ {rfq.rfq_number} — Priority: {rfq.priority.upper()}"
            body = _rfq_email_body(rfq, contact, action="New RFQ Received")
            result = await _send_email(
                settings.SALES_NOTIFY_EMAIL,
                subject,
                body,
                idempotency_key=f"rfq-new-{rfq_id}",
            )
            if not result.success:
                raise RuntimeError("New RFQ email delivery failed")
            return True
    except SQLAlchemyError:
        logger.exception("notify_new_rfq database error rfq_id=%s", rfq_id)
        raise
    except Exception:
        logger.exception("notify_new_rfq unexpected error rfq_id=%s", rfq_id)
        raise


async def notify_rfq_assigned(rfq_id: uuid.UUID) -> None:
    """Notify the assigned sales user."""
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq or not rfq.assigned_to:
                return
            assignee = await db.get(User, rfq.assigned_to)
            if not assignee or not getattr(assignee, "email", None):
                return
            subject = f"[ForgeBase] RFQ Assigned to You: {rfq.rfq_number}"
            body = _rfq_email_body(rfq, contact, action="RFQ Assigned to You")
            result = await _send_email(
                assignee.email,
                subject,
                body,
                idempotency_key=f"rfq-assigned-{rfq_id}-{assignee.id}",
            )
            if result.delivered:
                rfq.assigned_notified_at = utcnow_naive()
                db.add(rfq)
                await db.commit()
    except SQLAlchemyError:
        logger.exception("notify_rfq_assigned database error rfq_id=%s", rfq_id)
    except Exception:
        logger.exception("notify_rfq_assigned unexpected error rfq_id=%s", rfq_id)


async def notify_rfq_reminder(rfq_id: uuid.UUID) -> None:
    """24-hour reminder: RFQ still open / un-progressed."""
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq:
                return
            recipient = settings.SALES_NOTIFY_EMAIL
            if rfq.assigned_to:
                assignee = await db.get(User, rfq.assigned_to)
                if assignee and getattr(assignee, "email", None):
                    recipient = assignee.email
            subject = f"[ForgeBase] ⏰ 24h Reminder: {rfq.rfq_number} still open"
            body = _rfq_email_body(rfq, contact, action="24-Hour Reminder")
            result = None
            if recipient:
                result = await _send_email(
                    recipient,
                    subject,
                    body,
                    idempotency_key=f"rfq-reminder-24h-{rfq_id}",
                )
            if result and result.delivered:
                rfq.reminder_24h_sent_at = utcnow_naive()
                db.add(rfq)
                await db.commit()
    except SQLAlchemyError:
        logger.exception("notify_rfq_reminder database error rfq_id=%s", rfq_id)
    except Exception:
        logger.exception("notify_rfq_reminder unexpected error rfq_id=%s", rfq_id)


async def notify_rfq_escalation(rfq_id: uuid.UUID) -> None:
    """48-hour escalation: alert manager."""
    if not settings.MANAGER_EMAIL:
        return
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq:
                return
            subject = f"[ForgeBase] 🚨 48h Escalation: {rfq.rfq_number} no action taken"
            body = _rfq_email_body(rfq, contact, action="48-Hour Escalation — Manager Alert")
            result = await _send_email(
                settings.MANAGER_EMAIL,
                subject,
                body,
                idempotency_key=f"rfq-escalation-48h-{rfq_id}",
            )
            if result.delivered:
                rfq.escalation_48h_sent_at = utcnow_naive()
                db.add(rfq)
                await db.commit()
    except SQLAlchemyError:
        logger.exception("notify_rfq_escalation database error rfq_id=%s", rfq_id)
    except Exception:
        logger.exception("notify_rfq_escalation unexpected error rfq_id=%s", rfq_id)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_rfq_contact(
    rfq_id: uuid.UUID, db: AsyncSession
) -> tuple[Optional[RFQRequest], Optional[Contact]]:
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq:
        return None, None
    contact: Optional[Contact] = None
    if rfq.contact_id:
        contact = await db.get(Contact, rfq.contact_id)
    return rfq, contact


def _rfq_email_body(rfq: RFQRequest, contact: Optional[Contact], action: str) -> str:
    contact_name = html.escape(contact.full_name if contact else "Unknown", quote=True)
    contact_email = html.escape(contact.email if contact else "—", quote=True)
    contact_company = html.escape(contact.company_name if contact else "—", quote=True)
    action_display = html.escape(action, quote=True)
    admin_url = settings.ADMIN_URL.rstrip("/")
    return f"""
<html><body style="font-family: Arial, sans-serif; color: #333;">
<h2 style="color:#1a56db">ForgeBase — {action_display}</h2>
<table style="border-collapse:collapse;width:100%">
  <tr><td style="padding:8px;font-weight:bold;width:180px">RFQ Number</td><td style="padding:8px">{rfq.rfq_number}</td></tr>
  <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold">Contact</td><td style="padding:8px">{contact_name} ({contact_email})</td></tr>
  <tr><td style="padding:8px;font-weight:bold">Company</td><td style="padding:8px">{contact_company}</td></tr>
  <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold">Status</td><td style="padding:8px">{rfq.status}</td></tr>
  <tr><td style="padding:8px;font-weight:bold">Priority</td><td style="padding:8px">{rfq.priority.upper()}</td></tr>
  <tr style="background:#f9f9f9"><td style="padding:8px;font-weight:bold">Intent Score</td><td style="padding:8px">{rfq.intent_score_at_submit}</td></tr>
  <tr><td style="padding:8px;font-weight:bold">Submitted</td><td style="padding:8px">{rfq.created_at.strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
</table>
<p style="margin-top:20px">
  <a href="{admin_url}/dashboard/rfqs/{rfq.id}"
     style="background:#1a56db;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px">
    View RFQ in Admin
  </a>
</p>
</body></html>
"""
