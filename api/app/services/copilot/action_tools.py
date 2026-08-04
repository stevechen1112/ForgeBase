"""
AI Copilot — Write Action Tools

Tenant- and user-scoped mutations the assistant may perform after the user
explicitly asks (update RFQ status, queue follow-up email, add reminders).
"""
from __future__ import annotations

import html
import json
import logging
import uuid
from typing import Optional

from sqlmodel import select

from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.contact import Contact
from app.models.nurture import NurtureEnrollment, NurtureOutbox, NurtureSequence, NurtureStep
from app.models.rfq_event import RFQEvent
from app.models.rfq_request import RFQRequest

logger = logging.getLogger(__name__)

VALID_STATUSES = {
    "new", "assigned", "in_progress", "quoted", "negotiation", "won", "lost", "expired",
}
_FIRST_RESPONSE_STATUSES = {"assigned", "in_progress", "quoted", "negotiation"}
COPILOT_NURTURE_SEQ_PREFIX = "Copilot 草稿"
_WRITE_ROLES = frozenset({"admin", "owner", "marketing_manager"})


async def _get_rfq(s, tenant_id: uuid.UUID, rfq_number: str) -> RFQRequest | None:
    return (await s.exec(
        select(RFQRequest)
        .where(RFQRequest.tenant_id == tenant_id)
        .where(RFQRequest.rfq_number == rfq_number.upper().strip())
    )).first()


async def _log_rfq_event(
    s,
    rfq_id: uuid.UUID,
    event_type: str,
    summary: str,
    *,
    actor_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[uuid.UUID] = None,
    detail: Optional[str] = None,
) -> None:
    s.add(RFQEvent(
        rfq_id=rfq_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type=event_type,
        summary=summary,
        detail=detail,
    ))


async def _get_or_create_copilot_draft_sequence(
    s, tenant_id: uuid.UUID, subject: str,
) -> NurtureSequence:
    """One single-step sequence per draft so outbox send guard matches enrollment."""
    stamp = utcnow_naive().strftime("%Y%m%d-%H%M%S")
    label = subject.strip()[:40] or "跟進信"
    seq = NurtureSequence(
        tenant_id=tenant_id,
        name=f"{COPILOT_NURTURE_SEQ_PREFIX} {stamp} — {label}",
        description="由 AI 行銷助理建立的一次性跟進信，需人工核准後寄出",
        trigger_type="manual",
        is_active=True,
        is_approved=True,
        approved_at=utcnow_naive(),
    )
    s.add(seq)
    await s.flush()
    return seq


async def _load_contact_for_tenant(
    s, tenant_id: uuid.UUID, contact_id: uuid.UUID,
) -> Contact | None:
    contact = await s.get(Contact, contact_id)
    if not contact or contact.tenant_id != tenant_id:
        return None
    return contact


async def update_rfq_status(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    rfq_number: str,
    status: str,
    reason: Optional[str] = None,
) -> dict:
    """Update RFQ pipeline status (mirrors admin PUT /tracking/rfqs/{id}/status)."""
    if status not in VALID_STATUSES:
        return {"error": f"status must be one of: {', '.join(sorted(VALID_STATUSES))}"}

    async with get_session_ctx() as s:
        rfq = await _get_rfq(s, tenant_id, rfq_number)
        if not rfq:
            return {"error": f"RFQ {rfq_number} not found"}

        if status in ("won", "lost"):
            existing_reason = rfq.won_reason if status == "won" else rfq.lost_reason
            if not (reason and reason.strip()) and not existing_reason:
                return {
                    "error": f"標記為 {status} 時必須提供 reason（成交／流失原因）",
                }
            if reason and reason.strip():
                if status == "won":
                    rfq.won_reason = reason.strip()
                else:
                    rfq.lost_reason = reason.strip()

        old_status = rfq.status
        reason_only = old_status == status
        if reason_only:
            if status in ("won", "lost") and reason and reason.strip():
                s.add(rfq)
                await _log_rfq_event(
                    s, rfq.id, "status_changed",
                    f"{status} reason updated (via AI Copilot)",
                    actor_id=user_id,
                    tenant_id=tenant_id,
                    detail=json.dumps({"status": status, "source": "copilot", "reason_updated": True}),
                )
                await s.commit()
                return {
                    "success": True,
                    "rfq_number": rfq.rfq_number,
                    "status": rfq.status,
                    "message": f"已更新 {rfq.rfq_number} 的{('成交' if status == 'won' else '流失')}原因",
                }
            return {
                "success": True,
                "rfq_number": rfq.rfq_number,
                "status": rfq.status,
                "message": "狀態未變更（已是相同狀態）",
            }

        rfq.status = status
        rfq.updated_at = utcnow_naive()

        if old_status == "new" and status in _FIRST_RESPONSE_STATUSES and rfq.first_response_at is None:
            rfq.first_response_at = rfq.updated_at
        if status == "quoted" and rfq.quote_sent_at is None:
            rfq.quote_sent_at = rfq.updated_at
        if status in ("won", "lost", "expired"):
            rfq.closed_at = rfq.updated_at

        s.add(rfq)
        await _log_rfq_event(
            s, rfq.id, "status_changed",
            f"Status changed from {old_status} to {status} (via AI Copilot)",
            actor_id=user_id,
            tenant_id=tenant_id,
            detail=json.dumps({"old_status": old_status, "new_status": status, "source": "copilot"}),
        )
        await s.commit()

        try:
            from app.services.webhook import fire_webhook
            fire_webhook("rfq.status_changed", {
                "rfq_id": str(rfq.id),
                "rfq_number": rfq.rfq_number,
                "old_status": old_status,
                "new_status": rfq.status,
            })
        except Exception:
            logger.warning("rfq.status_changed webhook failed", exc_info=True)

        return {
            "success": True,
            "rfq_number": rfq.rfq_number,
            "old_status": old_status,
            "status": rfq.status,
            "message": f"已將 {rfq.rfq_number} 狀態更新為 {status}",
        }


async def record_rfq_first_response(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    rfq_number: str,
) -> dict:
    """Record that sales has responded to an RFQ (sets first_response_at)."""
    async with get_session_ctx() as s:
        rfq = await _get_rfq(s, tenant_id, rfq_number)
        if not rfq:
            return {"error": f"RFQ {rfq_number} not found"}

        if rfq.first_response_at:
            return {
                "success": True,
                "rfq_number": rfq.rfq_number,
                "first_response_at": rfq.first_response_at.isoformat(),
                "message": "首回時間已存在，未重複寫入",
            }

        now = utcnow_naive()
        rfq.first_response_at = now
        rfq.updated_at = now
        if rfq.status == "new":
            rfq.status = "in_progress"
        s.add(rfq)

        await _log_rfq_event(
            s, rfq.id, "first_response",
            "First response recorded (via AI Copilot)",
            actor_id=user_id,
            tenant_id=tenant_id,
        )
        await s.commit()

        return {
            "success": True,
            "rfq_number": rfq.rfq_number,
            "first_response_at": now.isoformat(),
            "status": rfq.status,
            "message": f"已記錄 {rfq.rfq_number} 的首回時間",
        }


async def assign_rfq_to_me(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    rfq_number: str,
) -> dict:
    """Assign an RFQ to the current logged-in user."""
    if not user_id:
        return {"error": "無法指派：缺少使用者身分"}

    async with get_session_ctx() as s:
        rfq = await _get_rfq(s, tenant_id, rfq_number)
        if not rfq:
            return {"error": f"RFQ {rfq_number} not found"}

        old_assigned = rfq.assigned_to
        if old_assigned == user_id:
            return {
                "success": True,
                "rfq_number": rfq.rfq_number,
                "status": rfq.status,
                "assigned_to": str(user_id),
                "message": f"{rfq.rfq_number} 已指派給你",
            }

        rfq.assigned_to = user_id
        rfq.status = "assigned"
        rfq.assigned_notified_at = None
        rfq.updated_at = utcnow_naive()
        s.add(rfq)

        await _log_rfq_event(
            s, rfq.id, "assigned",
            "Assigned to current user (via AI Copilot)",
            actor_id=user_id,
            tenant_id=tenant_id,
            detail=json.dumps({
                "old_assigned_to": str(old_assigned) if old_assigned else None,
                "new_assigned_to": str(user_id),
                "source": "copilot",
            }),
        )
        await s.commit()

        try:
            from app.services.notifications import notify_rfq_assigned
            import asyncio
            asyncio.create_task(notify_rfq_assigned(rfq.id))
        except Exception:
            logger.warning("rfq assign notification failed", exc_info=True)

        return {
            "success": True,
            "rfq_number": rfq.rfq_number,
            "status": rfq.status,
            "assigned_to": str(user_id),
            "message": f"已將 {rfq.rfq_number} 指派給你",
        }


async def queue_follow_up_email(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    contact_email: str,
    subject: str,
    body_text: str,
    rfq_number: Optional[str] = None,
) -> dict:
    """
    Queue a one-off follow-up email in the nurture outbox for manual approval.
    Does NOT send automatically.
    """
    email = contact_email.lower().strip()
    if not email or "@" not in email:
        return {"error": "contact_email 格式不正確"}
    if not subject.strip():
        return {"error": "subject 不可為空"}
    if not body_text.strip():
        return {"error": "body_text 不可為空"}

    async with get_session_ctx() as s:
        contact = (await s.exec(
            select(Contact)
            .where(Contact.tenant_id == tenant_id)
            .where(Contact.email == email)
        )).first()
        if not contact:
            return {"error": f"找不到聯絡人：{email}"}

        seq = await _get_or_create_copilot_draft_sequence(s, tenant_id, subject.strip())
        now = utcnow_naive()
        safe_body = html.escape(body_text.strip(), quote=False)

        step = NurtureStep(
            tenant_id=tenant_id,
            sequence_id=seq.id,
            step_order=0,
            delay_days=0,
            subject=subject.strip()[:500],
            text_body=body_text.strip(),
            html_body=f"<pre style='font-family:inherit;white-space:pre-wrap'>{safe_body}</pre>",
        )
        s.add(step)
        await s.flush()

        enrollment = NurtureEnrollment(
            tenant_id=tenant_id,
            sequence_id=seq.id,
            contact_id=contact.id,
            status="active",
            current_step=0,
            trigger_type="manual",
            trigger_value="copilot",
            enrolled_at=now,
        )
        s.add(enrollment)
        await s.flush()

        outbox = NurtureOutbox(
            tenant_id=tenant_id,
            enrollment_id=enrollment.id,
            sequence_id=seq.id,
            step_id=step.id,
            contact_id=contact.id,
            status="pending",
            subject=subject.strip()[:500],
            due_at=now,
        )
        s.add(outbox)

        if rfq_number:
            rfq = await _get_rfq(s, tenant_id, rfq_number)
            if rfq:
                await _log_rfq_event(
                    s, rfq.id, "copilot_follow_up_queued",
                    f"Follow-up email queued for approval: {subject.strip()[:120]}",
                    actor_id=user_id,
                    tenant_id=tenant_id,
                    detail=json.dumps({
                        "outbox_id": str(outbox.id),
                        "contact_email": email,
                        "source": "copilot",
                    }),
                )

        await s.commit()

        return {
            "success": True,
            "outbox_id": str(outbox.id),
            "contact_email": email,
            "subject": outbox.subject,
            "status": "pending",
            "message": "跟進信已加入寄送佇列，請至「自動化 → 寄送佇列」核准後寄出",
            "admin_path": "/dashboard/nurture/outbox",
        }


async def add_follow_up_reminder(
    tenant_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    title: str,
    description: str,
    contact_email: Optional[str] = None,
    rfq_number: Optional[str] = None,
) -> dict:
    """
    Append a follow-up reminder to a contact's notes (visible in CRM profile).
    Use when the user asks to add a to-do or reminder for later.
    """
    if not title.strip():
        return {"error": "title 不可為空"}

    stamp = utcnow_naive().strftime("%Y-%m-%d %H:%M")
    lines = [f"[AI助理待辦 {stamp}] {title.strip()}"]
    if description.strip():
        lines.append(description.strip())
    if rfq_number:
        lines.append(f"RFQ：{rfq_number.upper().strip()}")
    block = "\n".join(lines)

    async with get_session_ctx() as s:
        contact: Contact | None = None

        if contact_email:
            email = contact_email.lower().strip()
            contact = (await s.exec(
                select(Contact)
                .where(Contact.tenant_id == tenant_id)
                .where(Contact.email == email)
            )).first()
            if not contact:
                return {"error": f"找不到聯絡人：{email}"}
        elif rfq_number:
            rfq = await _get_rfq(s, tenant_id, rfq_number)
            if not rfq:
                return {"error": f"RFQ {rfq_number} not found"}
            if rfq.contact_id:
                contact = await _load_contact_for_tenant(s, tenant_id, rfq.contact_id)
            if not contact:
                return {"error": f"RFQ {rfq_number} 尚未連結聯絡人，請提供 contact_email"}
        else:
            return {"error": "請提供 contact_email 或 rfq_number 以寫入待辦"}

        existing = (contact.notes or "").strip()
        contact.notes = f"{existing}\n\n{block}".strip() if existing else block
        contact.updated_at = utcnow_naive()
        s.add(contact)

        if rfq_number:
            rfq_for_event = await _get_rfq(s, tenant_id, rfq_number)
            if rfq_for_event:
                await _log_rfq_event(
                    s, rfq_for_event.id, "copilot_reminder_added",
                    f"Follow-up reminder: {title.strip()[:120]}",
                    actor_id=user_id,
                    tenant_id=tenant_id,
                    detail=json.dumps({"source": "copilot", "title": title.strip()}),
                )

        await s.commit()

        return {
            "success": True,
            "contact_email": contact.email,
            "contact_name": contact.full_name,
            "reminder": block,
            "message": f"已將待辦寫入 {contact.full_name} 的聯絡人備註",
            "admin_path": f"/dashboard/contacts/{contact.id}",
        }
