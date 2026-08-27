"""Evidence-preserving North Star attribution derivation and overrides."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlmodel import select

from app.core.datetime import utcnow_naive
from app.models.attribution import AttributionEvent, AttributionLink
from app.models.inbound_reply import InboundReply, SalesHandoff, SalesHandoffEvent
from app.models.outreach import JourneySnapshot, OutreachMessage
from app.models.rfq_request import RFQRequest

AttributionType = Literal["direct", "assisted", "unknown", "manual"]


async def _handoff_for_rfq(db, rfq: RFQRequest) -> SalesHandoff | None:
    return (
        await db.exec(
            select(SalesHandoff).where(
                SalesHandoff.tenant_id == rfq.tenant_id,
                SalesHandoff.rfq_id == rfq.id,
            )
        )
    ).first()


async def _derive_lineage(
    db,
    *,
    rfq: RFQRequest,
    source_action: Literal["created_rfq", "linked_rfq"] | None = None,
) -> tuple[AttributionType, float, dict[str, Any], dict[str, uuid.UUID | None]]:
    """Derive only from tenant-consistent database links, never from email similarity."""
    handoff = await _handoff_for_rfq(db, rfq)
    empty = {
        "visitor_id": rfq.visitor_id,
        "company_identification_id": None,
        "contact_candidate_id": None,
        "contact_id": rfq.contact_id,
        "journey_snapshot_id": None,
        "outreach_message_id": None,
        "inbound_reply_id": None,
        "sales_handoff_id": None,
    }
    if not handoff:
        return (
            "unknown",
            0.0,
            {
                "rule": "no_verified_outreach_handoff_chain",
                "rfq_request_id": str(rfq.id),
                "source_page": rfq.source_page,
            },
            empty,
        )

    reply = await db.get(InboundReply, handoff.inbound_reply_id)
    message = await db.get(OutreachMessage, handoff.outreach_message_id)
    if (
        not reply
        or not message
        or reply.tenant_id != rfq.tenant_id
        or message.tenant_id != rfq.tenant_id
        or reply.outreach_message_id != message.id
        or handoff.outreach_message_id != message.id
    ):
        return (
            "unknown",
            0.0,
            {
                "rule": "broken_or_cross_tenant_handoff_chain",
                "rfq_request_id": str(rfq.id),
                "sales_handoff_id": str(handoff.id),
            },
            empty,
        )

    snapshot = await db.get(JourneySnapshot, message.journey_snapshot_id)
    if snapshot and snapshot.tenant_id != rfq.tenant_id:
        snapshot = None
    action = source_action
    if not action:
        action = (
            await db.exec(
                select(SalesHandoffEvent.action)
                .where(
                    SalesHandoffEvent.tenant_id == rfq.tenant_id,
                    SalesHandoffEvent.sales_handoff_id == handoff.id,
                    SalesHandoffEvent.action.in_(("created_rfq", "linked_rfq")),
                )
                .order_by(SalesHandoffEvent.created_at.asc())
                .limit(1)
            )
        ).first()
    if action not in {"created_rfq", "linked_rfq"}:
        action = "linked_rfq"
    attribution_type: AttributionType = (
        "direct" if action == "created_rfq" else "assisted"
    )
    confidence = 0.98 if attribution_type == "direct" else 0.80
    lineage = {
        "visitor_id": message.visitor_id,
        "company_identification_id": message.company_identification_id,
        "contact_candidate_id": message.contact_candidate_id,
        "contact_id": rfq.contact_id or message.contact_id,
        "journey_snapshot_id": snapshot.id if snapshot else None,
        "outreach_message_id": message.id,
        "inbound_reply_id": reply.id,
        "sales_handoff_id": handoff.id,
    }
    evidence = {
        "rule": (
            "rfq_created_from_reviewed_reply_handoff"
            if attribution_type == "direct"
            else "existing_rfq_linked_to_reviewed_reply_handoff"
        ),
        "causal_claim": (
            "direct_conversion"
            if attribution_type == "direct"
            else "assisted_only_no_direct_causal_claim"
        ),
        "rfq_request_id": str(rfq.id),
        **{key: str(value) if value else None for key, value in lineage.items()},
        "outreach_sent_at": message.sent_at.isoformat() if message.sent_at else None,
        "reply_received_at": reply.received_at.isoformat(),
        "handoff_created_at": handoff.created_at.isoformat(),
        "rfq_created_at": rfq.created_at.isoformat(),
        "reply_classification": reply.classification,
        "message_status": message.status,
    }
    return attribution_type, confidence, evidence, lineage


async def derive_attribution(
    db,
    *,
    rfq: RFQRequest,
    source_action: Literal["created_rfq", "linked_rfq"] | None = None,
    actor_user_id: uuid.UUID | None = None,
) -> AttributionLink:
    if not rfq.tenant_id:
        raise ValueError("Tenant-scoped RFQ is required for attribution")
    locked_rfq = (
        await db.exec(
            select(RFQRequest)
            .where(
                RFQRequest.id == rfq.id,
                RFQRequest.tenant_id == rfq.tenant_id,
            )
            .with_for_update()
        )
    ).first()
    if not locked_rfq:
        raise ValueError("RFQ is unavailable for attribution")
    rfq = locked_rfq
    existing = (
        await db.exec(
            select(AttributionLink)
            .where(
                AttributionLink.tenant_id == rfq.tenant_id,
                AttributionLink.rfq_request_id == rfq.id,
            )
            .with_for_update()
        )
    ).first()
    if existing and existing.manually_overridden:
        return existing

    attribution_type, confidence, evidence, lineage = await _derive_lineage(
        db, rfq=rfq, source_action=source_action
    )
    if (
        existing
        and existing.attribution_type == attribution_type
        and existing.confidence == confidence
        and existing.evidence == evidence
        and all(getattr(existing, key) == value for key, value in lineage.items())
    ):
        return existing
    now = utcnow_naive()
    previous_type = existing.attribution_type if existing else None
    if existing:
        row = existing
        action = "recalculated"
    else:
        row = AttributionLink(
            tenant_id=rfq.tenant_id,
            rfq_request_id=rfq.id,
            created_at=now,
        )
        action = "derived"
    for key, value in lineage.items():
        setattr(row, key, value)
    row.attribution_type = attribution_type
    row.confidence = confidence
    row.evidence = evidence
    row.updated_at = now
    db.add(row)
    await db.flush()
    db.add(
        AttributionEvent(
            tenant_id=rfq.tenant_id,
            attribution_link_id=row.id,
            rfq_request_id=rfq.id,
            actor_user_id=actor_user_id,
            action=action,
            previous_type=previous_type,
            attribution_type=attribution_type,
            confidence=confidence,
            reason=evidence["rule"],
            evidence=evidence,
            created_at=now,
        )
    )
    return row


async def override_attribution(
    db,
    *,
    rfq: RFQRequest,
    attribution_type: AttributionType,
    confidence: float,
    reason: str,
    actor_user_id: uuid.UUID,
) -> AttributionLink:
    row = (
        await db.exec(
            select(AttributionLink)
            .where(
                AttributionLink.tenant_id == rfq.tenant_id,
                AttributionLink.rfq_request_id == rfq.id,
            )
            .with_for_update()
        )
    ).first()
    if not row:
        row = await derive_attribution(db, rfq=rfq, actor_user_id=actor_user_id)
    if attribution_type == "direct" and row.attribution_type != "direct":
        raise ValueError("Direct attribution requires a verified RFQ-from-handoff chain")
    if attribution_type == "assisted" and not row.sales_handoff_id:
        raise ValueError("Assisted attribution requires a verified handoff link")
    now = utcnow_naive()
    previous_type = row.attribution_type
    automatic_evidence = dict(row.evidence)
    row.attribution_type = attribution_type
    row.confidence = confidence
    row.manually_overridden = True
    row.override_reason = reason.strip()
    row.overridden_by = actor_user_id
    row.overridden_at = now
    row.updated_at = now
    row.evidence = {
        **automatic_evidence,
        "manual_override": {
            "type": attribution_type,
            "confidence": confidence,
            "reason": reason.strip(),
            "actor_user_id": str(actor_user_id),
            "overridden_at": now.isoformat(),
        },
    }
    db.add(row)
    db.add(
        AttributionEvent(
            tenant_id=rfq.tenant_id,
            attribution_link_id=row.id,
            rfq_request_id=rfq.id,
            actor_user_id=actor_user_id,
            action="manual_override",
            previous_type=previous_type,
            attribution_type=attribution_type,
            confidence=confidence,
            reason=reason.strip(),
            evidence=row.evidence,
            created_at=now,
        )
    )
    return row


async def record_outcome_change(
    db,
    *,
    rfq: RFQRequest,
    previous_status: str,
    actor_user_id: uuid.UUID,
) -> None:
    if not rfq.tenant_id:
        return
    row = (
        await db.exec(
            select(AttributionLink).where(
                AttributionLink.tenant_id == rfq.tenant_id,
                AttributionLink.rfq_request_id == rfq.id,
            )
        )
    ).first()
    if not row:
        row = await derive_attribution(db, rfq=rfq, actor_user_id=actor_user_id)
    db.add(
        AttributionEvent(
            tenant_id=rfq.tenant_id,
            attribution_link_id=row.id,
            rfq_request_id=rfq.id,
            actor_user_id=actor_user_id,
            action="outcome_changed",
            previous_type=row.attribution_type,
            attribution_type=row.attribution_type,
            confidence=row.confidence,
            reason=f"RFQ status changed from {previous_status} to {rfq.status}",
            evidence={
                "old_status": previous_status,
                "new_status": rfq.status,
                "deal_amount": str(rfq.deal_amount) if rfq.deal_amount is not None else None,
                "deal_currency": rfq.deal_currency,
            },
            created_at=utcnow_naive(),
        )
    )
