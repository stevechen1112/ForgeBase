"""
Notification Service — 1b.4.7

Sends email notifications via SMTP (configurable).

Triggers:
  - notify_new_rfq(rfq_id)         — alert sales team of new RFQ
  - notify_rfq_assigned(rfq_id)    — notify assigned user
  - notify_rfq_reminder(rfq_id)    — 24-hour unacknowledged reminder
  - notify_rfq_escalation(rfq_id)  — 48-hour escalation to manager

SMTP config via env vars:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
  SALES_NOTIFY_EMAIL — fallback "all new RFQs" recipient
  MANAGER_EMAIL      — escalation recipient
"""
import logging
import os
import smtplib
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session_ctx
from app.models.rfq_request import RFQRequest
from app.models.contact import Contact
from app.models.user import User
from app.models.visitor import Visitor

logger = logging.getLogger(__name__)

# ── SMTP config ───────────────────────────────────────────────────────────────
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SALES_NOTIFY_EMAIL = os.getenv("SALES_NOTIFY_EMAIL", "")
MANAGER_EMAIL = os.getenv("MANAGER_EMAIL", "")


def _send_email(to: str, subject: str, body_html: str) -> bool:
    """Low-level SMTP send. Returns True on success."""
    if not SMTP_HOST or not to:
        logger.debug("SMTP not configured or empty recipient — skipping email")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, to, msg.as_string())
        return True
    except Exception as exc:
        logger.error("Email send failed to=%s: %s", to, exc)
        return False


async def notify_visitor_hot(visitor_id: uuid.UUID, stage: str, score: int) -> None:
    """
    Alert sales team when an anonymous visitor reaches hot/sales_ready
    without having submitted an RFQ. (1b.3.5 Intent trigger)
    """
    if not SALES_NOTIFY_EMAIL:
        return
    try:
        async with get_session_ctx() as db:
            visitor = await db.get(Visitor, visitor_id)
            contact_name = "Anonymous"
            contact_email = "—"
            if visitor and visitor.contact_id:
                contact = await db.get(Contact, visitor.contact_id)
                if contact:
                    contact_name = contact.full_name
                    contact_email = contact.email
            stage_label = stage.replace("_", " ").title()
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
  <a href="https://admin.forgebase.io/dashboard/visitors/{visitor_id}"
     style="background:#1a56db;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px">
    View Visitor Profile
  </a>
</p>
</body></html>
"""
            _send_email(SALES_NOTIFY_EMAIL, subject, body)
    except Exception as exc:
        logger.error("notify_visitor_hot error visitor_id=%s: %s", visitor_id, exc)


# ── Notification triggers ─────────────────────────────────────────────────────

async def notify_new_rfq(rfq_id: uuid.UUID) -> None:
    """Alert the configured sales inbox about a new RFQ."""
    if not SALES_NOTIFY_EMAIL:
        return
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq:
                return
            subject = f"[ForgeBase] New RFQ {rfq.rfq_number} — Priority: {rfq.priority.upper()}"
            body = _rfq_email_body(rfq, contact, action="New RFQ Received")
            _send_email(SALES_NOTIFY_EMAIL, subject, body)
    except Exception as exc:
        logger.error("notify_new_rfq error rfq_id=%s: %s", rfq_id, exc)


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
            if _send_email(assignee.email, subject, body):
                rfq.assigned_notified_at = utcnow_naive()
                db.add(rfq)
                await db.commit()
    except Exception as exc:
        logger.error("notify_rfq_assigned error rfq_id=%s: %s", rfq_id, exc)


async def notify_rfq_reminder(rfq_id: uuid.UUID) -> None:
    """24-hour reminder: RFQ still open / un-progressed."""
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq:
                return
            recipient = SALES_NOTIFY_EMAIL
            if rfq.assigned_to:
                assignee = await db.get(User, rfq.assigned_to)
                if assignee and getattr(assignee, "email", None):
                    recipient = assignee.email
            subject = f"[ForgeBase] ⏰ 24h Reminder: {rfq.rfq_number} still open"
            body = _rfq_email_body(rfq, contact, action="24-Hour Reminder")
            if recipient and _send_email(recipient, subject, body):
                rfq.reminder_24h_sent_at = utcnow_naive()
                db.add(rfq)
                await db.commit()
    except Exception as exc:
        logger.error("notify_rfq_reminder error rfq_id=%s: %s", rfq_id, exc)


async def notify_rfq_escalation(rfq_id: uuid.UUID) -> None:
    """48-hour escalation: alert manager."""
    if not MANAGER_EMAIL:
        return
    try:
        async with get_session_ctx() as db:
            rfq, contact = await _load_rfq_contact(rfq_id, db)
            if not rfq:
                return
            subject = f"[ForgeBase] 🚨 48h Escalation: {rfq.rfq_number} no action taken"
            body = _rfq_email_body(rfq, contact, action="48-Hour Escalation — Manager Alert")
            if _send_email(MANAGER_EMAIL, subject, body):
                rfq.escalation_48h_sent_at = utcnow_naive()
                db.add(rfq)
                await db.commit()
    except Exception as exc:
        logger.error("notify_rfq_escalation error rfq_id=%s: %s", rfq_id, exc)


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
    contact_name = contact.full_name if contact else "Unknown"
    contact_email = contact.email if contact else "—"
    contact_company = contact.company_name if contact else "—"
    return f"""
<html><body style="font-family: Arial, sans-serif; color: #333;">
<h2 style="color:#1a56db">ForgeBase — {action}</h2>
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
  <a href="https://admin.forgebase.io/dashboard/rfqs/{rfq.id}"
     style="background:#1a56db;color:#fff;padding:10px 20px;text-decoration:none;border-radius:4px">
    View RFQ in Admin
  </a>
</p>
</body></html>
"""
