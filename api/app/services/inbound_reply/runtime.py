"""Resend inbound receipt ingestion and deterministic reply processing."""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import timedelta
from email.utils import parseaddr

from sqlalchemy import or_
from sqlmodel import col, select

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.encryption import encrypt
from app.db.session import get_session_ctx
from app.models.inbound_reply import (
    InboundReply,
    InboundReplyPolicy,
    SalesHandoff,
    SalesHandoffEvent,
)
from app.models.outreach import OutreachDeliveryPolicy, OutreachMessage
from app.models.tenant import Tenant
from app.services.email_governance import email_hash, mask_email, normalize_email
from app.services.inbound_reply.classification import classify_reply
from app.services.inbound_reply.jobs import enqueue_inbound_reply_fetch
from app.services.inbound_reply.provider import fetch_received_email
from app.services.inbound_reply.routing import (
    parse_reply_route,
    route_hash,
    validate_reply_route,
)
from app.services.inbound_reply.sanitize import (
    body_to_safe_text,
    clean_text,
    safe_attachment_metadata,
)
from app.services.notification_router import send_notification
from app.services.outreach.delivery import cancel_queued_for_hash, record_suppression
from app.services.capability_access import tenant_has_feature

_MESSAGE_ID = re.compile(r"<[^<>\r\n]{1,480}>")
_HANDOFF_CLASSIFICATIONS = {"positive", "question", "rfq"}
_TERMINAL_OUTREACH = {"bounced", "complained", "unsubscribed"}
logger = logging.getLogger(__name__)


async def redact_expired_inbound_content(db, *, limit: int = 100) -> int:
    """Remove decrypted-capable content while retaining non-PII audit linkage."""
    now = utcnow_naive()
    rows = list(
        (
            await db.exec(
                select(InboundReply)
                .where(
                    InboundReply.expires_at <= now,
                    InboundReply.content_redacted_at.is_(None),
                )
                .order_by(col(InboundReply.expires_at))
                .limit(max(1, min(limit, 1000)))
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    for row in rows:
        row.sender_email_ciphertext = encrypt("")
        row.subject_ciphertext = encrypt("[content expired]")
        row.body_text_ciphertext = None
        row.body_char_count = 0
        row.attachment_metadata = []
        row.attachment_count = 0
        row.attachment_total_bytes = 0
        row.attachments_quarantined = False
        row.content_redacted_at = now
        row.updated_at = now
        db.add(row)
    return len(rows)


async def mark_breached_handoff_slas(db, *, limit: int = 100) -> int:
    """Persist overdue open handoffs so operational metrics do not depend on UI time."""
    now = utcnow_naive()
    rows = list(
        (
            await db.exec(
                select(SalesHandoff)
                .where(
                    SalesHandoff.sla_breached.is_(False),
                    SalesHandoff.sla_due_at < now,
                    SalesHandoff.status.notin_(["converted_to_rfq", "closed"]),
                )
                .order_by(col(SalesHandoff.sla_due_at))
                .limit(max(1, min(limit, 1000)))
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    for row in rows:
        row.sla_breached = True
        row.updated_at = now
        db.add(row)
    return len(rows)


def _addresses(value) -> list[str]:
    rows = value if isinstance(value, list) else [value]
    result: list[str] = []
    for item in rows:
        address = parseaddr(str(item or ""))[1].strip().lower()
        if "@" in address and address not in result:
            result.append(address)
    return result[:50]


def _safe_headers(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    allowed = {
        "auto-submitted",
        "in-reply-to",
        "precedence",
        "references",
        "x-autoreply",
        "x-autorespond",
    }
    return {
        str(key).lower(): clean_text(str(raw), limit=4000)
        for key, raw in value.items()
        if str(key).lower() in allowed
    }


def _thread_ids(headers: dict[str, str]) -> tuple[str | None, list[str]]:
    in_reply_to = (_MESSAGE_ID.findall(headers.get("in-reply-to", "")) or [None])[0]
    references = _MESSAGE_ID.findall(headers.get("references", ""))[:50]
    return in_reply_to, list(dict.fromkeys(references))


async def _route_message(
    db, recipients: list[str]
) -> tuple[OutreachMessage | None, str | None]:
    for address in recipients:
        parsed = parse_reply_route(address)
        if not parsed:
            continue
        message = await db.get(OutreachMessage, parsed[0])
        address_digest = route_hash(address)
        if (
            message
            and message.sent_reply_to
            and message.reply_route_token_hash == address_digest
            and route_hash(message.sent_reply_to) == address_digest
            and validate_reply_route(
                address,
                message_id=message.id,
                tenant_id=message.tenant_id,
                email_digest=message.to_email_hash,
            )
        ):
            return message, route_hash(address)
    return None, None


async def ingest_resend_receipt(
    db,
    *,
    payload: dict,
    provider_event_id: str,
    raw_payload_sha256: str,
) -> tuple[InboundReply | None, bool, bool]:
    """Persist bounded metadata; return (receipt, should_enqueue, created)."""
    if not settings.INBOUND_REPLY_ENABLED:
        return None, False, False
    data = payload.get("data") or {}
    provider_email_id = str(data.get("email_id") or "")[:120]
    sender = parseaddr(str(data.get("from") or ""))[1].strip().lower()
    if not provider_email_id or "@" not in sender:
        return None, False, False
    existing = (
        await db.exec(
            select(InboundReply).where(
                InboundReply.provider == "resend",
                or_(
                    InboundReply.provider_event_id == provider_event_id,
                    InboundReply.provider_email_id == provider_email_id,
                ),
            )
        )
    ).first()
    if existing:
        return existing, False, False

    recipients = _addresses(data.get("to")) + _addresses(data.get("received_for"))
    message, address_hash = await _route_message(db, recipients)
    policy = await db.get(InboundReplyPolicy, message.tenant_id) if message else None
    tenant = await db.get(Tenant, message.tenant_id) if message else None
    enabled = bool(
        message
        and tenant
        and settings.INBOUND_REPLY_ENABLED
        and policy
        and policy.mode == "review_only"
        and tenant_has_feature(tenant, "inbound_reply")
    )
    now = utcnow_naive()
    retention_days = policy.content_retention_days if policy else 7
    receipt = InboundReply(
        tenant_id=message.tenant_id if message else None,
        outreach_message_id=message.id if message else None,
        provider_event_id=provider_event_id,
        provider_email_id=provider_email_id,
        rfc_message_id=clean_text(str(data.get("message_id") or ""), limit=500) or None,
        sender_email_ciphertext=encrypt(normalize_email(sender)),
        sender_email_hash=email_hash(sender),
        sender_email_masked=mask_email(sender),
        route_address_hash=address_hash,
        subject_ciphertext=encrypt(
            clean_text(str(data.get("subject") or ""), limit=500)
        ),
        attachment_count=min(
            len(data.get("attachments") or [])
            if isinstance(data.get("attachments"), list)
            else 0,
            10000,
        ),
        attachments_quarantined=bool(data.get("attachments")),
        status="fetch_pending" if enabled else "needs_review",
        processing_error=None
        if enabled
        else "Inbound route or tenant policy requires review",
        raw_payload_sha256=raw_payload_sha256,
        received_at=now,
        expires_at=now + timedelta(days=retention_days),
        created_at=now,
        updated_at=now,
    )
    db.add(receipt)
    if enabled:
        enqueue_inbound_reply_fetch(
            db, tenant_id=message.tenant_id, inbound_reply_id=receipt.id
        )
    return receipt, enabled, True


async def _link_by_thread(
    db, reply: InboundReply, thread_ids: list[str]
) -> OutreachMessage | None:
    if not thread_ids:
        return None
    filters = [InboundReply.rfc_message_id.in_(thread_ids)]
    if reply.tenant_id:
        filters.append(InboundReply.tenant_id == reply.tenant_id)
    parent = (
        await db.exec(
            select(InboundReply)
            .where(*filters)
            .order_by(InboundReply.received_at.desc())
        )
    ).first()
    if not parent or not parent.outreach_message_id or not parent.tenant_id:
        return None
    reply.parent_reply_id = parent.id
    reply.tenant_id = parent.tenant_id
    reply.outreach_message_id = parent.outreach_message_id
    return await db.get(OutreachMessage, parent.outreach_message_id)


async def run_inbound_reply_fetch(reply_id: uuid.UUID) -> None:
    async with get_session_ctx() as db:
        reply = (
            await db.exec(
                select(InboundReply)
                .where(InboundReply.id == reply_id)
                .with_for_update()
            )
        ).first()
        if not reply:
            return
        if reply.status in {"classified", "handed_off", "ignored"}:
            return
        if not settings.INBOUND_REPLY_ENABLED:
            reply.status = "failed"
            reply.processing_error = "Inbound reply processing kill switch is off"
            reply.updated_at = utcnow_naive()
            db.add(reply)
            await db.commit()
            return
        reply.status = "processing"
        reply.updated_at = utcnow_naive()
        db.add(reply)
        await db.commit()
        provider_email_id = reply.provider_email_id

    payload = await fetch_received_email(provider_email_id)
    headers = _safe_headers(payload.get("headers"))
    in_reply_to, references = _thread_ids(headers)
    subject = clean_text(str(payload.get("subject") or ""), limit=500)
    body = body_to_safe_text(payload.get("text"), payload.get("html"))
    sender = parseaddr(str(payload.get("from") or ""))[1].strip().lower()
    attachments, attachment_bytes, quarantined = safe_attachment_metadata(
        payload.get("attachments")
    )
    classification = classify_reply(subject, body, headers)
    now = utcnow_naive()
    handoff_id: uuid.UUID | None = None
    notify_tenant: uuid.UUID | None = None

    async with get_session_ctx() as db:
        reply = (
            await db.exec(
                select(InboundReply)
                .where(InboundReply.id == reply_id)
                .with_for_update()
            )
        ).first()
        if not reply or reply.status in {"classified", "handed_off", "ignored"}:
            return
        if "@" not in sender or email_hash(sender) != reply.sender_email_hash:
            reply.status = "needs_review"
            reply.processing_error = (
                "Webhook and Receiving API sender identity mismatch"
            )
            reply.updated_at = now
            db.add(reply)
            await db.commit()
            return
        message = (
            await db.get(OutreachMessage, reply.outreach_message_id)
            if reply.outreach_message_id
            else None
        )
        if not message:
            message = await _link_by_thread(
                db, reply, [item for item in [in_reply_to, *references] if item]
            )
        if not message or not reply.tenant_id:
            reply.status = "needs_review"
            reply.processing_error = "No verified outreach thread match"
            reply.updated_at = now
            db.add(reply)
            await db.commit()
            return
        tenant = await db.get(Tenant, reply.tenant_id)
        policy = await db.get(InboundReplyPolicy, reply.tenant_id)
        if (
            not tenant
            or not policy
            or policy.mode != "review_only"
            or not tenant_has_feature(tenant, "inbound_reply")
        ):
            reply.status = "failed"
            reply.processing_error = "Tenant inbound reply policy is off"
            reply.updated_at = now
            db.add(reply)
            await db.commit()
            return

        reply.rfc_message_id = (
            clean_text(str(payload.get("message_id") or ""), limit=500)
            or reply.rfc_message_id
        )
        reply.in_reply_to = in_reply_to
        reply.references = references
        reply.subject_ciphertext = encrypt(subject)
        reply.body_text_ciphertext = encrypt(body) if body else None
        reply.body_sha256 = hashlib.sha256(body.encode()).hexdigest() if body else None
        reply.body_char_count = len(body)
        reply.attachment_metadata = attachments
        reply.attachment_count = len(attachments)
        reply.attachment_total_bytes = attachment_bytes
        reply.attachments_quarantined = quarantined
        reply.classification = classification.label
        reply.classification_confidence = classification.confidence
        reply.classification_reasons = classification.reasons
        reply.stops_automation = classification.is_human
        reply.needs_human_review = classification.label not in {"auto_reply", "bounce"}
        reply.fetched_at = now
        reply.classified_at = now
        reply.processing_error = None
        reply.updated_at = now

        if classification.is_human:
            await cancel_queued_for_hash(
                db,
                email_digest=message.to_email_hash,
                tenant_id=message.tenant_id,
                reason="Human reply received",
            )
            if message.status not in _TERMINAL_OUTREACH:
                message.status = "replied"
                message.updated_at = now
                db.add(message)

        if classification.label == "unsubscribe":
            delivery_policy = await db.get(OutreachDeliveryPolicy, message.tenant_id)
            scope = delivery_policy.unsubscribe_scope if delivery_policy else "tenant"
            await record_suppression(
                db,
                tenant_id=message.tenant_id,
                email_digest=message.to_email_hash,
                email_masked=message.to_email_masked,
                scope=scope,
                reason="reply_unsubscribe",
                source_event_id=f"inbound:{reply.provider_event_id}",
            )
            message.status = "unsubscribed"
            message.unsubscribed_at = now
            message.updated_at = now
            reply.status = "classified"
        elif classification.label in {"auto_reply", "bounce"}:
            reply.status = "ignored"
        elif classification.label in _HANDOFF_CLASSIFICATIONS and tenant_has_feature(
            tenant, "sales_handoff"
        ):
            handoff = (
                await db.exec(
                    select(SalesHandoff).where(
                        SalesHandoff.inbound_reply_id == reply.id
                    )
                )
            ).first()
            if not handoff:
                priority = "urgent" if classification.label == "rfq" else "high"
                handoff = SalesHandoff(
                    tenant_id=reply.tenant_id,
                    inbound_reply_id=reply.id,
                    outreach_message_id=message.id,
                    priority=priority,
                    classification=classification.label,
                    summary=f"{classification.label} reply from {reply.sender_email_masked}: {subject[:300]}",
                    sla_due_at=now + timedelta(hours=policy.handoff_sla_hours),
                    created_at=now,
                    updated_at=now,
                )
                db.add(handoff)
                db.add(
                    SalesHandoffEvent(
                        tenant_id=reply.tenant_id,
                        sales_handoff_id=handoff.id,
                        action="created",
                        detail={"classification": classification.label},
                        created_at=now,
                    )
                )
            reply.status = "handed_off"
            handoff_id = handoff.id
            notify_tenant = reply.tenant_id
        else:
            reply.status = "needs_review"
        db.add(reply)
        await db.commit()

    if notify_tenant and handoff_id:
        try:
            await send_notification(
                notify_tenant,
                "chat_handoff",
                "New buyer email reply is ready for human sales follow-up.",
                event_ref_id=handoff_id,
            )
        except Exception:
            logger.exception("Inbound handoff notification failed for %s", handoff_id)
