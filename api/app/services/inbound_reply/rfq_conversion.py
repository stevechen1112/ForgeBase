"""Human-reviewed conversion of a sales handoff into the existing RFQ work queue."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import func, text
from sqlmodel import col, select

from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt
from app.models.contact import Contact
from app.models.contact_enrichment import ContactCandidate
from app.models.inbound_reply import InboundReply, SalesHandoff
from app.models.outreach import JourneySnapshot, OutreachMessage
from app.models.rfq_event import RFQEvent
from app.models.rfq_request import RFQRequest
from app.services.email_governance import normalize_email


async def _allocate_rfq_number(db) -> str:
    now = utcnow_naive()
    prefix = f"RFQ-{now:%Y%m%d}-"
    if db.get_bind().dialect.name == "postgresql":
        await db.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": f"forgebase-rfq-{now:%Y%m%d}"},
        )
    latest = (
        await db.exec(
            select(RFQRequest.rfq_number)
            .where(col(RFQRequest.rfq_number).like(f"{prefix}%"))
            .order_by(col(RFQRequest.rfq_number).desc())
            .limit(1)
        )
    ).first()
    try:
        sequence = int(latest.rsplit("-", 1)[-1]) + 1 if latest else 1
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("Malformed RFQ number sequence") from exc
    return f"{prefix}{sequence:03d}"


async def create_rfq_from_handoff(
    db,
    *,
    handoff: SalesHandoff,
    actor_id: uuid.UUID,
) -> RFQRequest:
    """Create one tenant-scoped RFQ without pretending a public form was submitted."""
    if handoff.rfq_id:
        existing = await db.get(RFQRequest, handoff.rfq_id)
        if existing and existing.tenant_id == handoff.tenant_id:
            return existing

    reply = await db.get(InboundReply, handoff.inbound_reply_id)
    message = await db.get(OutreachMessage, handoff.outreach_message_id)
    if not reply or not message:
        raise ValueError("Handoff source records are unavailable")
    if reply.tenant_id != handoff.tenant_id or message.tenant_id != handoff.tenant_id:
        raise ValueError("Handoff source tenant mismatch")

    candidate = await db.get(ContactCandidate, message.contact_candidate_id)
    snapshot = await db.get(JourneySnapshot, message.journey_snapshot_id)
    sender_email = normalize_email(decrypt(reply.sender_email_ciphertext))
    if not sender_email:
        raise ValueError("Reply sender email is unavailable")
    sender_matches_original_recipient = reply.sender_email_hash == message.to_email_hash

    contact = (
        await db.exec(
            select(Contact).where(
                Contact.tenant_id == handoff.tenant_id,
                func.lower(Contact.email) == sender_email.lower(),
            )
        )
    ).first()
    now = utcnow_naive()
    if not contact:
        contact = Contact(
            tenant_id=handoff.tenant_id,
            email=sender_email,
            full_name=(
                candidate.full_name
                if candidate and sender_matches_original_recipient
                else reply.sender_email_masked
            ),
            company_name=(
                candidate.source_company_name
                if candidate and sender_matches_original_recipient
                else None
            ),
            job_title=(
                candidate.job_title
                if candidate and sender_matches_original_recipient
                else None
            ),
            source_type="inbound_outreach_reply",
            source_reference_id=reply.id,
            created_at=now,
            updated_at=now,
        )
        db.add(contact)
        await db.flush()

    subject = decrypt(reply.subject_ciphertext)
    body = decrypt(reply.body_text_ciphertext) if reply.body_text_ciphertext else ""
    source_snapshot = {
        "source": "human_reviewed_inbound_outreach_reply",
        "inbound_reply_id": str(reply.id),
        "sales_handoff_id": str(handoff.id),
        "outreach_message_id": str(message.id),
        "sender_email_masked": reply.sender_email_masked,
        "subject": subject,
        "message": body,
        "original_outreach_company_name": candidate.source_company_name
        if candidate
        else None,
        "original_outreach_candidate_name": candidate.full_name if candidate else None,
        "sender_matches_original_recipient": sender_matches_original_recipient,
        "consent": None,
        "conversion_actor_id": str(actor_id),
        "converted_at": now.isoformat(),
    }
    rfq = RFQRequest(
        tenant_id=handoff.tenant_id,
        rfq_number=await _allocate_rfq_number(db),
        contact_id=contact.id,
        visitor_id=message.visitor_id,
        form_data=json.dumps(source_snapshot, ensure_ascii=False),
        source_context_json=json.dumps(
            {
                "source": "outreach_reply_handoff",
                "outreach_message_id": str(message.id),
                "inbound_reply_id": str(reply.id),
                "sales_handoff_id": str(handoff.id),
            }
        ),
        status="new",
        priority=handoff.priority,
        source_page="inbound-email",
        is_test_data=False,
        created_at=now,
        updated_at=now,
    )
    db.add(rfq)
    await db.flush()
    db.add(
        RFQEvent(
            rfq_id=rfq.id,
            tenant_id=handoff.tenant_id,
            actor_id=actor_id,
            event_type="created_from_handoff",
            summary=f"{rfq.rfq_number} created from reviewed inbound reply",
            detail=json.dumps(
                {
                    "sales_handoff_id": str(handoff.id),
                    "inbound_reply_id": str(reply.id),
                    "outreach_message_id": str(message.id),
                }
            ),
        )
    )
    return rfq
