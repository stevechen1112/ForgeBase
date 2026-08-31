"""Tenant reply inbox, sales handoff queue, and restricted unlinked review."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import (
    get_current_user,
    require_rfq_manager,
    require_rfq_operator,
    require_superuser,
    require_user_tenant_id,
)
from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt
from app.db.session import get_session
from app.models.company_identification import CompanyIdentification
from app.models.contact_enrichment import ContactCandidate
from app.models.inbound_reply import (
    InboundReply,
    InboundReplyPolicy,
    SalesHandoff,
    SalesHandoffEvent,
)
from app.models.outreach import JourneySnapshot, OutreachDeliveryPolicy, OutreachMessage
from app.models.platform_audit_log import PlatformAuditLog
from app.models.rfq_request import RFQRequest
from app.models.tenant import Tenant
from app.models.user import User
from app.services.attribution import derive_attribution
from app.services.inbound_reply.jobs import ensure_inbound_reply_fetch
from app.services.inbound_reply.rfq_conversion import create_rfq_from_handoff
from app.services.inbound_reply.routing import inbound_route_configured
from app.services.operational_outbox import enqueue_operational_job
from app.services.outreach.delivery import cancel_queued_for_hash, record_suppression
from app.services.capability_access import tenant_has_feature

tracking_router = APIRouter(prefix="/tracking", tags=["Inbound Replies"])
admin_router = APIRouter(prefix="/admin/inbound-replies", tags=["Inbound Reply Review"])
DbDep = Annotated[AsyncSession, Depends(get_session)]
OperatorDep = Annotated[User, Depends(require_rfq_operator)]
ManagerDep = Annotated[User, Depends(require_rfq_manager)]
SuperuserDep = Annotated[User, Depends(require_superuser)]


async def require_reply_viewer(
    current_user: User = Depends(get_current_user),  # noqa: B008
) -> User:
    if current_user.role not in {"admin", "owner", "marketing_manager", "sales"}:
        raise HTTPException(status_code=403, detail="Reply inbox access required")
    return current_user


ViewerDep = Annotated[User, Depends(require_reply_viewer)]


class InboundPolicyIn(BaseModel):
    mode: Literal["off", "review_only"] = "off"
    handoff_sla_hours: int = Field(default=4, ge=1, le=168)
    content_retention_days: int = Field(default=90, ge=1, le=365)


class ReplyClassifyIn(BaseModel):
    classification: Literal[
        "unknown",
        "positive",
        "question",
        "rfq",
        "not_now",
        "wrong_person",
        "unsubscribe",
        "negative",
        "auto_reply",
        "bounce",
    ]
    note: str = Field(min_length=1, max_length=2000)


class HandoffActionIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


class HandoffAssignIn(BaseModel):
    owner_id: uuid.UUID
    note: str | None = Field(default=None, max_length=2000)


class LinkRfqIn(BaseModel):
    rfq_id: uuid.UUID
    note: str | None = Field(default=None, max_length=2000)


class LinkUnmatchedIn(BaseModel):
    outreach_message_id: uuid.UUID
    note: str = Field(min_length=1, max_length=2000)


def _audit(
    db: AsyncSession,
    actor: User,
    *,
    tenant_id: uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: uuid.UUID,
    changes: dict,
) -> None:
    db.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            changes_json=json.dumps(changes, default=str),
        )
    )


def _policy_dict(row: InboundReplyPolicy, *, persisted: bool) -> dict:
    return {
        "tenant_id": str(row.tenant_id),
        "mode": row.mode,
        "handoff_sla_hours": row.handoff_sla_hours,
        "content_retention_days": row.content_retention_days,
        "route_configured": inbound_route_configured(),
        "updated_by": str(row.updated_by) if row.updated_by else None,
        "updated_at": row.updated_at.isoformat(),
        "persisted": persisted,
    }


def _reply_summary(row: InboundReply) -> dict:
    return {
        "id": str(row.id),
        "outreach_message_id": str(row.outreach_message_id)
        if row.outreach_message_id
        else None,
        "parent_reply_id": str(row.parent_reply_id) if row.parent_reply_id else None,
        "sender_email_masked": row.sender_email_masked,
        "classification": row.classification,
        "classification_confidence": row.classification_confidence,
        "classification_reasons": row.classification_reasons,
        "status": row.status,
        "stops_automation": row.stops_automation,
        "needs_human_review": row.needs_human_review,
        "attachment_count": row.attachment_count,
        "attachment_total_bytes": row.attachment_total_bytes,
        "attachments_quarantined": row.attachments_quarantined,
        "received_at": row.received_at.isoformat(),
        "classified_at": row.classified_at.isoformat() if row.classified_at else None,
        "fetched_at": row.fetched_at.isoformat() if row.fetched_at else None,
        "expires_at": row.expires_at.isoformat(),
        "content_redacted_at": row.content_redacted_at.isoformat()
        if row.content_redacted_at
        else None,
    }


def _handoff_dict(row: SalesHandoff) -> dict:
    now = utcnow_naive()
    return {
        "id": str(row.id),
        "inbound_reply_id": str(row.inbound_reply_id),
        "outreach_message_id": str(row.outreach_message_id),
        "rfq_id": str(row.rfq_id) if row.rfq_id else None,
        "owner_id": str(row.owner_id) if row.owner_id else None,
        "status": row.status,
        "priority": row.priority,
        "classification": row.classification,
        "summary": row.summary,
        "sla_due_at": row.sla_due_at.isoformat(),
        "sla_breached": row.sla_breached
        or (row.status not in {"converted_to_rfq", "closed"} and row.sla_due_at < now),
        "accepted_at": row.accepted_at.isoformat() if row.accepted_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


async def _tenant_reply(
    db: AsyncSession, reply_id: uuid.UUID, tenant_id: uuid.UUID, *, lock: bool = False
) -> InboundReply:
    statement = select(InboundReply).where(
        InboundReply.id == reply_id,
        InboundReply.tenant_id == tenant_id,
    )
    if lock:
        statement = statement.with_for_update()
    row = (await db.exec(statement)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Inbound reply not found")
    return row


async def _tenant_handoff(
    db: AsyncSession, handoff_id: uuid.UUID, tenant_id: uuid.UUID, *, lock: bool = False
) -> SalesHandoff:
    statement = select(SalesHandoff).where(
        SalesHandoff.id == handoff_id,
        SalesHandoff.tenant_id == tenant_id,
    )
    if lock:
        statement = statement.with_for_update()
    row = (await db.exec(statement)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Sales handoff not found")
    return row


def _event(
    db: AsyncSession,
    row: SalesHandoff,
    actor: User,
    action: str,
    *,
    note: str | None = None,
    detail: dict | None = None,
) -> None:
    db.add(
        SalesHandoffEvent(
            tenant_id=row.tenant_id,
            sales_handoff_id=row.id,
            actor_user_id=actor.id,
            action=action,
            note=note,
            detail=json.loads(json.dumps(detail or {}, default=str)),
        )
    )


def _assert_owner_or_manager(row: SalesHandoff, actor: User) -> None:
    if actor.role in {"admin", "owner"}:
        return
    if row.owner_id and row.owner_id != actor.id:
        raise HTTPException(
            status_code=403, detail="Handoff belongs to another sales user"
        )


@tracking_router.get("/replies/policy")
async def get_inbound_policy(db: DbDep, current_user: ViewerDep):
    tenant_id = require_user_tenant_id(current_user)
    row = await db.get(InboundReplyPolicy, tenant_id)
    if row:
        return _policy_dict(row, persisted=True)
    return _policy_dict(InboundReplyPolicy(tenant_id=tenant_id), persisted=False)


@tracking_router.put("/replies/policy")
async def update_inbound_policy(
    body: InboundPolicyIn, db: DbDep, current_user: ManagerDep
):
    tenant_id = require_user_tenant_id(current_user)
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.mode == "review_only":
        missing = [
            feature
            for feature in ("inbound_reply", "sales_handoff")
            if not tenant_has_feature(tenant, feature)
        ]
        if missing:
            raise HTTPException(
                status_code=409,
                detail=f"Tenant features are disabled: {', '.join(missing)}",
            )
        if not inbound_route_configured():
            raise HTTPException(
                status_code=409, detail="Inbound reply route is not ready"
            )
    now = utcnow_naive()
    row = await db.get(InboundReplyPolicy, tenant_id)
    before = _policy_dict(row, persisted=True) if row else None
    if not row:
        row = InboundReplyPolicy(tenant_id=tenant_id, created_at=now)
    row.mode = body.mode
    row.handoff_sla_hours = body.handoff_sla_hours
    row.content_retention_days = body.content_retention_days
    row.updated_by = current_user.id
    row.updated_at = now
    db.add(row)
    _audit(
        db,
        current_user,
        tenant_id=tenant_id,
        action="inbound_reply.policy_update",
        target_type="inbound_reply_policy",
        target_id=tenant_id,
        changes={"before": before, "after": body.model_dump()},
    )
    await db.commit()
    await db.refresh(row)
    return _policy_dict(row, persisted=True)


@tracking_router.get("/replies")
async def list_replies(
    db: DbDep,
    current_user: ViewerDep,
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    classification: str | None = Query(default=None, max_length=30),
    received_from: datetime | None = None,
    received_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    tenant_id = require_user_tenant_id(current_user)
    filters = [InboundReply.tenant_id == tenant_id]
    if status_filter:
        filters.append(InboundReply.status == status_filter)
    if classification:
        filters.append(InboundReply.classification == classification)
    if received_from:
        filters.append(InboundReply.received_at >= received_from)
    if received_to:
        filters.append(InboundReply.received_at <= received_to)
    total = (
        await db.exec(select(func.count()).select_from(InboundReply).where(*filters))
    ).one()
    rows = (
        await db.exec(
            select(InboundReply)
            .where(*filters)
            .order_by(col(InboundReply.received_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [_reply_summary(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tracking_router.get("/replies/{reply_id}")
async def get_reply(reply_id: uuid.UUID, db: DbDep, current_user: ViewerDep):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_reply(db, reply_id, tenant_id)
    message = (
        await db.get(OutreachMessage, row.outreach_message_id)
        if row.outreach_message_id
        else None
    )
    thread = []
    if message:
        thread = (
            await db.exec(
                select(InboundReply)
                .where(
                    InboundReply.tenant_id == tenant_id,
                    InboundReply.outreach_message_id == message.id,
                )
                .order_by(InboundReply.received_at)
            )
        ).all()
    sender = decrypt(row.sender_email_ciphertext)
    subject = decrypt(row.subject_ciphertext)
    snapshot = (
        await db.get(JourneySnapshot, message.journey_snapshot_id) if message else None
    )
    candidate = (
        await db.get(ContactCandidate, message.contact_candidate_id)
        if message
        else None
    )
    company = (
        await db.get(CompanyIdentification, message.company_identification_id)
        if message
        else None
    )
    return {
        **_reply_summary(row),
        "subject": subject,
        "body_text": decrypt(row.body_text_ciphertext)
        if row.body_text_ciphertext
        else None,
        "attachment_metadata": row.attachment_metadata,
        "processing_error": row.processing_error,
        "original_outreach": {
            "id": str(message.id),
            "subject": message.subject_snapshot,
            "text": message.text_snapshot,
            "journey_snapshot_id": str(message.journey_snapshot_id),
        }
        if message
        else None,
        "buyer_context": {
            "sender_matches_outreach_recipient": bool(
                message and row.sender_email_hash == message.to_email_hash
            ),
            "company_name": company.company_name if company else None,
            "company_domain": company.domain if company else None,
            "company_confidence": company.confidence if company else None,
            "candidate_name": candidate.full_name if candidate else None,
            "candidate_title": candidate.job_title if candidate else None,
            "candidate_source_provider": candidate.source_provider
            if candidate
            else None,
            "journey_summary": snapshot.summary if snapshot else None,
            "top_products": snapshot.top_products if snapshot else [],
        },
        "thread": [_reply_summary(item) for item in thread],
        "reply_externally_url": (
            f"mailto:{quote(sender)}?subject={quote(f'Re: {subject}')}"
            if sender and current_user.role in {"admin", "owner", "sales"}
            else None
        ),
    }


@tracking_router.post("/replies/{reply_id}/classify")
async def classify_reply_manually(
    reply_id: uuid.UUID,
    body: ReplyClassifyIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_reply(db, reply_id, tenant_id, lock=True)
    row.classification = body.classification
    row.classification_confidence = 1.0
    row.classification_reasons = ["human_review"]
    row.needs_human_review = False
    row.stops_automation = body.classification not in {"auto_reply", "bounce"}
    row.updated_at = utcnow_naive()
    if body.classification in {"auto_reply", "bounce"}:
        row.status = "ignored"
    else:
        row.status = "classified"
    message = (
        await db.get(OutreachMessage, row.outreach_message_id)
        if row.outreach_message_id
        else None
    )
    if row.stops_automation and message:
        await cancel_queued_for_hash(
            db,
            email_digest=message.to_email_hash,
            tenant_id=tenant_id,
            reason=f"Human-classified inbound reply: {body.classification}",
        )
    if body.classification == "unsubscribe" and message:
        delivery_policy = await db.get(OutreachDeliveryPolicy, tenant_id)
        await record_suppression(
            db,
            tenant_id=tenant_id,
            email_digest=message.to_email_hash,
            email_masked=message.to_email_masked,
            scope=delivery_policy.unsubscribe_scope if delivery_policy else "tenant",
            reason="reply_unsubscribe",
            source_event_id=f"inbound:{row.provider_event_id}:human",
        )
        message.status = "unsubscribed"
        message.unsubscribed_at = message.unsubscribed_at or utcnow_naive()
        message.updated_at = utcnow_naive()
        db.add(message)
    db.add(row)
    _audit(
        db,
        current_user,
        tenant_id=tenant_id,
        action="inbound_reply.classify",
        target_type="inbound_reply",
        target_id=row.id,
        changes={"classification": body.classification, "note": body.note},
    )
    await db.commit()
    return _reply_summary(row)


@tracking_router.post("/replies/{reply_id}/handoff")
async def create_handoff(
    reply_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    reply = await _tenant_reply(db, reply_id, tenant_id, lock=True)
    if not reply.outreach_message_id:
        raise HTTPException(
            status_code=409, detail="Reply has no verified outreach thread"
        )
    if reply.classification in {"auto_reply", "bounce", "unsubscribe"}:
        raise HTTPException(
            status_code=409,
            detail="This classification cannot become a sales handoff",
        )
    existing = (
        await db.exec(
            select(SalesHandoff).where(SalesHandoff.inbound_reply_id == reply.id)
        )
    ).first()
    if existing:
        return _handoff_dict(existing)
    policy = await db.get(InboundReplyPolicy, tenant_id)
    now = utcnow_naive()
    row = SalesHandoff(
        tenant_id=tenant_id,
        inbound_reply_id=reply.id,
        outreach_message_id=reply.outreach_message_id,
        owner_id=current_user.id,
        status="accepted",
        priority="urgent" if reply.classification == "rfq" else "high",
        classification=reply.classification,
        summary=f"{reply.classification} reply from {reply.sender_email_masked}",
        sla_due_at=now + timedelta(hours=policy.handoff_sla_hours if policy else 4),
        accepted_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    _event(db, row, current_user, "created", note=body.note)
    _event(db, row, current_user, "accepted", note=body.note)
    reply.status = "handed_off"
    reply.needs_human_review = False
    reply.updated_at = now
    db.add(reply)
    await db.commit()
    return _handoff_dict(row)


@tracking_router.post("/replies/{reply_id}/fetch")
async def retry_reply_fetch(
    reply_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: ManagerDep,
):
    tenant_id = require_user_tenant_id(current_user)
    reply = await _tenant_reply(db, reply_id, tenant_id, lock=True)
    if reply.fetched_at:
        raise HTTPException(status_code=409, detail="Reply content was already fetched")
    tenant = await db.get(Tenant, tenant_id)
    policy = await db.get(InboundReplyPolicy, tenant_id)
    if (
        not tenant
        or not policy
        or policy.mode != "review_only"
        or not tenant_has_feature(tenant, "inbound_reply")
        or not tenant_has_feature(tenant, "sales_handoff")
        or not inbound_route_configured()
    ):
        raise HTTPException(
            status_code=409, detail="Inbound reply processing is not ready"
        )
    reply.status = "fetch_pending"
    reply.processing_error = None
    reply.updated_at = utcnow_naive()
    db.add(reply)
    await ensure_inbound_reply_fetch(db, tenant_id=tenant_id, inbound_reply_id=reply.id)
    _audit(
        db,
        current_user,
        tenant_id=tenant_id,
        action="inbound_reply.fetch_retry",
        target_type="inbound_reply",
        target_id=reply.id,
        changes={"note": body.note},
    )
    await db.commit()
    return _reply_summary(reply)


@tracking_router.get("/sales-handoffs")
async def list_handoffs(
    db: DbDep,
    current_user: ViewerDep,
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    owner_id: uuid.UUID | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    tenant_id = require_user_tenant_id(current_user)
    filters = [SalesHandoff.tenant_id == tenant_id]
    if status_filter:
        filters.append(SalesHandoff.status == status_filter)
    if owner_id:
        filters.append(SalesHandoff.owner_id == owner_id)
    if created_from:
        filters.append(SalesHandoff.created_at >= created_from)
    if created_to:
        filters.append(SalesHandoff.created_at <= created_to)
    total = (
        await db.exec(select(func.count()).select_from(SalesHandoff).where(*filters))
    ).one()
    rows = (
        await db.exec(
            select(SalesHandoff)
            .where(*filters)
            .order_by(col(SalesHandoff.created_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [_handoff_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@tracking_router.get("/sales-handoffs/{handoff_id}")
async def get_handoff(handoff_id: uuid.UUID, db: DbDep, current_user: ViewerDep):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id)
    events = (
        await db.exec(
            select(SalesHandoffEvent)
            .where(
                SalesHandoffEvent.tenant_id == tenant_id,
                SalesHandoffEvent.sales_handoff_id == row.id,
            )
            .order_by(SalesHandoffEvent.created_at)
        )
    ).all()
    return {
        **_handoff_dict(row),
        "events": [
            {
                "id": str(event.id),
                "action": event.action,
                "actor_user_id": str(event.actor_user_id)
                if event.actor_user_id
                else None,
                "note": event.note,
                "detail": event.detail,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ],
    }


@tracking_router.post("/sales-handoffs/{handoff_id}/accept")
async def accept_handoff(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    if row.status in {"converted_to_rfq", "closed"}:
        raise HTTPException(status_code=409, detail="Handoff is already closed")
    if row.owner_id and row.owner_id != current_user.id:
        raise HTTPException(status_code=409, detail="Handoff already has another owner")
    now = utcnow_naive()
    row.owner_id = current_user.id
    row.status = "accepted"
    row.accepted_at = row.accepted_at or now
    row.updated_at = now
    db.add(row)
    _event(db, row, current_user, "accepted", note=body.note)
    await db.commit()
    return _handoff_dict(row)


@tracking_router.post("/sales-handoffs/{handoff_id}/assign")
async def assign_handoff(
    handoff_id: uuid.UUID,
    body: HandoffAssignIn,
    db: DbDep,
    current_user: ManagerDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    owner = await db.get(User, body.owner_id)
    if (
        not owner
        or owner.tenant_id != tenant_id
        or owner.role not in {"admin", "owner", "sales"}
    ):
        raise HTTPException(
            status_code=400, detail="Owner is not a tenant sales operator"
        )
    if row.status in {"converted_to_rfq", "closed"}:
        raise HTTPException(status_code=409, detail="Handoff is already closed")
    previous = row.owner_id
    row.owner_id = owner.id
    row.status = "accepted"
    row.accepted_at = row.accepted_at or utcnow_naive()
    row.updated_at = utcnow_naive()
    db.add(row)
    _event(
        db,
        row,
        current_user,
        "assigned",
        note=body.note,
        detail={"previous_owner_id": previous, "owner_id": owner.id},
    )
    await db.commit()
    return _handoff_dict(row)


@tracking_router.post("/sales-handoffs/{handoff_id}/start")
async def start_handoff(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    _assert_owner_or_manager(row, current_user)
    if row.status in {"converted_to_rfq", "closed"}:
        raise HTTPException(status_code=409, detail="Handoff is already closed")
    now = utcnow_naive()
    row.owner_id = row.owner_id or current_user.id
    row.accepted_at = row.accepted_at or now
    row.status = "in_progress"
    row.updated_at = now
    db.add(row)
    _event(db, row, current_user, "started", note=body.note)
    await db.commit()
    return _handoff_dict(row)


@tracking_router.post("/sales-handoffs/{handoff_id}/contacted")
async def mark_contacted(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    _assert_owner_or_manager(row, current_user)
    if row.status in {"converted_to_rfq", "closed"}:
        raise HTTPException(status_code=409, detail="Handoff is already closed")
    row.status = "in_progress"
    row.owner_id = row.owner_id or current_user.id
    row.accepted_at = row.accepted_at or utcnow_naive()
    row.updated_at = utcnow_naive()
    db.add(row)
    _event(db, row, current_user, "contacted", note=body.note)
    await db.commit()
    return _handoff_dict(row)


async def _finish_handoff(
    db: AsyncSession,
    row: SalesHandoff,
    actor: User,
    *,
    action: Literal["marked_wrong_person", "unsubscribed", "closed"],
    note: str | None,
) -> None:
    _assert_owner_or_manager(row, actor)
    message = await db.get(OutreachMessage, row.outreach_message_id)
    reply = await db.get(InboundReply, row.inbound_reply_id)
    now = utcnow_naive()
    if action in {"marked_wrong_person", "unsubscribed"} and message:
        delivery_policy = await db.get(OutreachDeliveryPolicy, row.tenant_id)
        policy_scope = (
            delivery_policy.unsubscribe_scope if delivery_policy else "tenant"
        )
        await record_suppression(
            db,
            tenant_id=row.tenant_id,
            email_digest=message.to_email_hash,
            email_masked=message.to_email_masked,
            scope=policy_scope,
            reason="wrong_person"
            if action == "marked_wrong_person"
            else "manual_unsubscribe",
            source_event_id=f"handoff:{row.id}:{action}",
        )
        await cancel_queued_for_hash(
            db,
            email_digest=message.to_email_hash,
            tenant_id=row.tenant_id,
            reason=action,
        )
        message.status = "unsubscribed" if action == "unsubscribed" else "cancelled"
        message.updated_at = now
        db.add(message)
    if reply:
        reply.classification = (
            "wrong_person"
            if action == "marked_wrong_person"
            else ("unsubscribe" if action == "unsubscribed" else reply.classification)
        )
        reply.needs_human_review = False
        reply.updated_at = now
        db.add(reply)
    row.status = "closed"
    row.closed_at = now
    row.updated_at = now
    db.add(row)
    _event(db, row, actor, action, note=note)


@tracking_router.post("/sales-handoffs/{handoff_id}/wrong-person")
async def mark_wrong_person(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    await _finish_handoff(
        db, row, current_user, action="marked_wrong_person", note=body.note
    )
    await db.commit()
    return _handoff_dict(row)


@tracking_router.post("/sales-handoffs/{handoff_id}/unsubscribe")
async def unsubscribe_handoff(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    await _finish_handoff(db, row, current_user, action="unsubscribed", note=body.note)
    await db.commit()
    return _handoff_dict(row)


@tracking_router.post("/sales-handoffs/{handoff_id}/close")
async def close_handoff(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    await _finish_handoff(db, row, current_user, action="closed", note=body.note)
    await db.commit()
    return _handoff_dict(row)


async def _link_handoff_rfq(
    db: AsyncSession,
    *,
    row: SalesHandoff,
    rfq: RFQRequest,
    actor: User,
    action: Literal["linked_rfq", "created_rfq"],
    note: str | None,
) -> dict:
    now = utcnow_naive()
    row.rfq_id = rfq.id
    row.status = "converted_to_rfq"
    row.closed_at = now
    row.updated_at = now
    db.add(row)
    _event(db, row, actor, action, note=note, detail={"rfq_id": rfq.id})
    await db.flush()
    await derive_attribution(
        db,
        rfq=rfq,
        source_action=action,
        actor_user_id=actor.id,
    )
    return {**_handoff_dict(row), "rfq_number": rfq.rfq_number}


@tracking_router.post("/sales-handoffs/{handoff_id}/link-rfq")
async def link_handoff_rfq(
    handoff_id: uuid.UUID,
    body: LinkRfqIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    _assert_owner_or_manager(row, current_user)
    rfq = await db.get(RFQRequest, body.rfq_id)
    if not rfq or rfq.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if row.rfq_id:
        if row.rfq_id != rfq.id:
            raise HTTPException(
                status_code=409, detail="Handoff is already linked to an RFQ"
            )
        return {**_handoff_dict(row), "rfq_number": rfq.rfq_number}
    if row.status == "closed":
        raise HTTPException(status_code=409, detail="Closed handoff cannot link an RFQ")
    result = await _link_handoff_rfq(
        db,
        row=row,
        rfq=rfq,
        actor=current_user,
        action="linked_rfq",
        note=body.note,
    )
    await db.commit()
    return result


@tracking_router.post("/sales-handoffs/{handoff_id}/convert-to-rfq")
async def convert_handoff_to_rfq(
    handoff_id: uuid.UUID,
    body: HandoffActionIn,
    db: DbDep,
    current_user: OperatorDep,
):
    tenant_id = require_user_tenant_id(current_user)
    row = await _tenant_handoff(db, handoff_id, tenant_id, lock=True)
    _assert_owner_or_manager(row, current_user)
    if row.rfq_id:
        existing = await db.get(RFQRequest, row.rfq_id)
        if existing and existing.tenant_id == tenant_id:
            return {**_handoff_dict(row), "rfq_number": existing.rfq_number}
    if row.status == "closed":
        raise HTTPException(
            status_code=409, detail="Closed handoff cannot create an RFQ"
        )
    try:
        rfq = await create_rfq_from_handoff(db, handoff=row, actor_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    result = await _link_handoff_rfq(
        db,
        row=row,
        rfq=rfq,
        actor=current_user,
        action="created_rfq",
        note=body.note,
    )
    for job_type in (
        "rfq_route",
        "rfq_notify",
    ):
        payload = {"rfq_id": str(rfq.id)}
        enqueue_operational_job(
            db,
            job_type=job_type,
            payload=payload,
            idempotency_key=f"rfq:{rfq.id}:{job_type.removeprefix('rfq_')}",
            tenant_id=tenant_id,
        )
    await db.commit()
    return result


@admin_router.get("/unlinked")
async def list_unlinked_replies(
    db: DbDep,
    _current_user: SuperuserDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
):
    filters = [InboundReply.tenant_id.is_(None)]
    total = (
        await db.exec(select(func.count()).select_from(InboundReply).where(*filters))
    ).one()
    rows = (
        await db.exec(
            select(InboundReply)
            .where(*filters)
            .order_by(col(InboundReply.received_at).desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "items": [_reply_summary(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@admin_router.post("/{reply_id}/link")
async def link_unmatched_reply(
    reply_id: uuid.UUID,
    body: LinkUnmatchedIn,
    db: DbDep,
    current_user: SuperuserDep,
):
    reply = (
        await db.exec(
            select(InboundReply).where(InboundReply.id == reply_id).with_for_update()
        )
    ).first()
    if not reply:
        raise HTTPException(status_code=404, detail="Inbound reply not found")
    message = await db.get(OutreachMessage, body.outreach_message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Outreach message not found")
    if reply.tenant_id and reply.tenant_id != message.tenant_id:
        raise HTTPException(
            status_code=409, detail="Reply is already linked to another tenant"
        )
    reply.tenant_id = message.tenant_id
    reply.outreach_message_id = message.id
    tenant = await db.get(Tenant, message.tenant_id)
    policy = await db.get(InboundReplyPolicy, message.tenant_id)
    ready = bool(
        tenant
        and policy
        and policy.mode == "review_only"
        and tenant_has_feature(tenant, "inbound_reply")
        and tenant_has_feature(tenant, "sales_handoff")
        and inbound_route_configured()
    )
    reply.status = "fetch_pending" if ready else "needs_review"
    reply.processing_error = None if ready else "Tenant inbound processing is not ready"
    reply.expires_at = utcnow_naive() + timedelta(
        days=policy.content_retention_days if policy else 7
    )
    reply.updated_at = utcnow_naive()
    db.add(reply)
    if ready:
        await ensure_inbound_reply_fetch(
            db, tenant_id=message.tenant_id, inbound_reply_id=reply.id
        )
    _audit(
        db,
        current_user,
        tenant_id=message.tenant_id,
        action="inbound_reply.manual_link",
        target_type="inbound_reply",
        target_id=reply.id,
        changes={
            "outreach_message_id": str(message.id),
            "note": body.note,
        },
    )
    await db.commit()
    return _reply_summary(reply)
