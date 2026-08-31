"""Platform review queue and explicitly human-approved outreach delivery."""

from __future__ import annotations

import hashlib
import html
import json
import uuid
from datetime import timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_superuser
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.contact_enrichment import ContactCandidate
from app.models.email_delivery import EmailDeliveryEvent
from app.models.operational_job import OperationalJob
from app.models.outreach import (
    JourneySnapshot,
    OutreachDeliveryPolicy,
    OutreachDraftPolicy,
    OutreachMessage,
    OutreachMessageReview,
)
from app.models.platform_audit_log import PlatformAuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.services.outreach.content_guard import (
    OutreachContentError,
    OutreachDraftBlocked,
    canonical_cta,
    validate_content,
)
from app.services.outreach.delivery import cancel_queued_for_hash, record_suppression
from app.services.outreach.jobs import (
    enqueue_journey_summarize_job,
    enqueue_outreach_send_job,
)
from app.services.outreach.runtime import validate_message_for_approval
from app.services.outreach.unsubscribe import (
    InvalidUnsubscribeToken,
    token_hash,
    verify_unsubscribe_token,
)
from app.services.resend_webhook import resend_webhook_signing_configured
from app.services.capability_access import tenant_has_feature

router = APIRouter(prefix="/admin/outreach", tags=["Outreach Review and Delivery"])
public_router = APIRouter(prefix="/outreach", tags=["Outreach Preferences"])
DbDep = Annotated[AsyncSession, Depends(get_session)]
SuperuserDep = Annotated[User, Depends(require_superuser)]


class OutreachPolicyUpdate(BaseModel):
    mode: Literal["off", "review_only"] = "off"
    lookback_days: int = Field(default=30, ge=1, le=365)
    snapshot_retention_days: int = Field(default=90, ge=1, le=365)
    max_evidence_events: int = Field(default=100, ge=1, le=500)
    allowed_languages: list[str] = Field(
        default_factory=lambda: ["en", "zh-TW"], min_length=1, max_length=20
    )
    policy_version: str = Field(
        default="outreach-review-v1", min_length=1, max_length=60
    )

    @field_validator("allowed_languages")
    @classmethod
    def clean_languages(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if not cleaned or any(len(item) > 10 for item in cleaned):
            raise ValueError("At least one valid language is required")
        return cleaned


class DraftRevisionIn(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body_without_cta: str = Field(min_length=1, max_length=5000)
    note: str = Field(min_length=1, max_length=2000)


class DraftDecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def rejection_reason(self):
        if self.decision == "reject" and not (self.reason_code or self.note):
            raise ValueError("A rejection reason is required")
        return self


class DeliveryPolicyUpdate(BaseModel):
    mode: Literal["off", "approval_send"] = "off"
    provider_name: Literal["resend"] = "resend"
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    quiet_hours_enabled: bool = True
    quiet_start_hour: int = Field(default=20, ge=0, le=23)
    quiet_end_hour: int = Field(default=8, ge=0, le=23)
    daily_send_quota: int = Field(default=10, ge=0, le=10000)
    frequency_cap_days: int = Field(default=30, ge=1, le=365)
    unsubscribe_scope: Literal["tenant", "global"] = "tenant"
    controlled_auto_opt_in: bool = False
    controlled_auto_legal_approved: bool = False
    controlled_auto_allowed_regions: list[str] = Field(
        default_factory=list, max_length=100
    )
    controlled_auto_allowed_personas: list[str] = Field(
        default_factory=list, max_length=100
    )
    controlled_auto_allowed_templates: list[str] = Field(
        default_factory=list, max_length=100
    )
    controlled_auto_review_sample_pct: int = Field(default=100, ge=1, le=100)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Unknown IANA timezone") from exc
        return value

    @field_validator(
        "controlled_auto_allowed_regions",
        "controlled_auto_allowed_personas",
        "controlled_auto_allowed_templates",
    )
    @classmethod
    def clean_controlled_auto_allowlist(cls, value: list[str]) -> list[str]:
        cleaned = list(dict.fromkeys(item.strip() for item in value if item.strip()))
        if any(len(item) > 120 for item in cleaned):
            raise ValueError(
                "Controlled Auto allowlist values must be at most 120 characters"
            )
        return cleaned

    @model_validator(mode="after")
    def controlled_auto_requires_narrow_scope(self):
        if self.controlled_auto_opt_in and (
            not self.controlled_auto_allowed_regions
            or not self.controlled_auto_allowed_personas
            or not self.controlled_auto_allowed_templates
        ):
            raise ValueError(
                "Controlled Auto opt-in requires region, persona and template "
                "allowlists"
            )
        return self


class DeliveryActionIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


def _audit(
    db: AsyncSession,
    actor: User,
    tenant_id: uuid.UUID,
    action: str,
    target_id: uuid.UUID,
    changes: dict,
) -> None:
    db.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action=action,
            target_type="outreach_message",
            target_id=str(target_id),
            changes_json=json.dumps(changes, default=str),
        )
    )


async def _tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


def _policy_dict(row: OutreachDraftPolicy, persisted: bool = True) -> dict:
    return {
        "tenant_id": str(row.tenant_id),
        "mode": row.mode,
        "lookback_days": row.lookback_days,
        "snapshot_retention_days": row.snapshot_retention_days,
        "max_evidence_events": row.max_evidence_events,
        "allowed_languages": row.allowed_languages,
        "policy_version": row.policy_version,
        "updated_by": str(row.updated_by) if row.updated_by else None,
        "updated_at": row.updated_at.isoformat(),
        "persisted": persisted,
    }


def _snapshot_dict(row: JourneySnapshot) -> dict:
    return {
        "id": str(row.id),
        "visitor_id": str(row.visitor_id),
        "company_identification_id": str(row.company_identification_id),
        "top_products": row.top_products,
        "top_pages": row.top_pages,
        "downloads": row.downloads,
        "comparisons": row.comparisons,
        "cta_signals": row.cta_signals,
        "journey_signals": row.journey_signals,
        "summary": row.summary,
        "evidence_event_ids": row.evidence_event_ids,
        "knowledge_references": row.knowledge_references,
        "policy_version": row.policy_version,
        "generated_at": row.generated_at.isoformat(),
        "expires_at": row.expires_at.isoformat(),
    }


def _message_dict(
    row: OutreachMessage, snapshot: JourneySnapshot | None = None
) -> dict:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "company_identification_id": str(row.company_identification_id),
        "contact_candidate_id": str(row.contact_candidate_id),
        "contact_id": str(row.contact_id) if row.contact_id else None,
        "journey_snapshot_id": str(row.journey_snapshot_id),
        "revision_of_id": str(row.revision_of_id) if row.revision_of_id else None,
        "revision_no": row.revision_no,
        "purpose": row.purpose,
        "channel": row.channel,
        "language": row.language,
        "to_email_masked": row.to_email_masked,
        "identity_notice": "This is a company-related business contact candidate, not an identified anonymous visitor.",
        "subject": row.subject_snapshot,
        "html": row.html_snapshot,
        "text": row.text_snapshot,
        "personalization_evidence": row.personalization_evidence,
        "knowledge_version": row.knowledge_version,
        "prompt_version": row.prompt_version,
        "policy_version": row.policy_version,
        "generation_model": row.generation_model,
        "content_hash": row.content_hash,
        "status": row.status,
        "approved_by": str(row.approved_by) if row.approved_by else None,
        "approved_at": row.approved_at.isoformat() if row.approved_at else None,
        "rejected_by": str(row.rejected_by) if row.rejected_by else None,
        "rejected_at": row.rejected_at.isoformat() if row.rejected_at else None,
        "review_note": row.review_note,
        "created_by": str(row.created_by) if row.created_by else None,
        "generated_at": row.generated_at.isoformat(),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "journey_snapshot": _snapshot_dict(snapshot) if snapshot else None,
        "send_available": row.status == "approved",
        "send_requested_at": row.send_requested_at.isoformat()
        if row.send_requested_at
        else None,
        "scheduled_for": row.scheduled_for.isoformat() if row.scheduled_for else None,
        "send_attempts": row.send_attempts,
        "provider": row.provider,
        "provider_message_id": row.provider_message_id,
        "sent_at": row.sent_at.isoformat() if row.sent_at else None,
        "delivered_at": row.delivered_at.isoformat() if row.delivered_at else None,
        "opened_at": row.opened_at.isoformat() if row.opened_at else None,
        "clicked_at": row.clicked_at.isoformat() if row.clicked_at else None,
        "bounced_at": row.bounced_at.isoformat() if row.bounced_at else None,
        "complained_at": row.complained_at.isoformat() if row.complained_at else None,
        "unsubscribed_at": row.unsubscribed_at.isoformat()
        if row.unsubscribed_at
        else None,
        "last_error": row.last_error,
    }


def _delivery_policy_dict(row: OutreachDeliveryPolicy, persisted: bool = True) -> dict:
    return {
        "tenant_id": str(row.tenant_id),
        "mode": row.mode,
        "provider_name": row.provider_name,
        "timezone": row.timezone,
        "quiet_hours_enabled": row.quiet_hours_enabled,
        "quiet_start_hour": row.quiet_start_hour,
        "quiet_end_hour": row.quiet_end_hour,
        "daily_send_quota": row.daily_send_quota,
        "frequency_cap_days": row.frequency_cap_days,
        "unsubscribe_scope": row.unsubscribe_scope,
        "controlled_auto_opt_in": row.controlled_auto_opt_in,
        "controlled_auto_legal_approved": row.controlled_auto_legal_approved,
        "controlled_auto_allowed_regions": row.controlled_auto_allowed_regions,
        "controlled_auto_allowed_personas": row.controlled_auto_allowed_personas,
        "controlled_auto_allowed_templates": row.controlled_auto_allowed_templates,
        "controlled_auto_review_sample_pct": row.controlled_auto_review_sample_pct,
        "controlled_auto_reviewed_by": str(row.controlled_auto_reviewed_by)
        if row.controlled_auto_reviewed_by
        else None,
        "controlled_auto_reviewed_at": row.controlled_auto_reviewed_at.isoformat()
        if row.controlled_auto_reviewed_at
        else None,
        "updated_by": str(row.updated_by) if row.updated_by else None,
        "updated_at": row.updated_at.isoformat(),
        "persisted": persisted,
        "readiness": {
            "ready": bool(
                settings.EMAIL_EXTERNAL_DELIVERY_ENABLED
                and settings.OUTREACH_SEND_ENABLED
                and settings.RESEND_API_KEY.strip()
                and settings.OUTREACH_PUBLIC_BASE_URL.strip().startswith(
                    ("https://", "http://")
                )
                and (
                    not settings.is_production
                    or settings.OUTREACH_PUBLIC_BASE_URL.strip().startswith("https://")
                )
                and len(settings.OUTREACH_UNSUBSCRIBE_SECRET.strip()) >= 32
                and resend_webhook_signing_configured()
            ),
            "external_delivery_enabled": settings.EMAIL_EXTERNAL_DELIVERY_ENABLED,
            "outreach_send_enabled": settings.OUTREACH_SEND_ENABLED,
            "provider_configured": bool(settings.RESEND_API_KEY.strip()),
            "public_url_configured": settings.OUTREACH_PUBLIC_BASE_URL.strip().startswith(
                ("https://", "http://")
            )
            and (
                not settings.is_production
                or settings.OUTREACH_PUBLIC_BASE_URL.strip().startswith("https://")
            ),
            "unsubscribe_signing_configured": len(
                settings.OUTREACH_UNSUBSCRIBE_SECRET.strip()
            )
            >= 32,
            "webhook_signing_configured": resend_webhook_signing_configured(),
        },
    }


@router.get("/policies/{tenant_id}")
async def get_policy(tenant_id: uuid.UUID, db: DbDep, _: SuperuserDep):
    await _tenant(db, tenant_id)
    row = await db.get(OutreachDraftPolicy, tenant_id)
    return (
        _policy_dict(row)
        if row
        else _policy_dict(OutreachDraftPolicy(tenant_id=tenant_id), False)
    )


@router.put("/policies/{tenant_id}")
async def update_policy(
    tenant_id: uuid.UUID, body: OutreachPolicyUpdate, db: DbDep, actor: SuperuserDep
):
    await _tenant(db, tenant_id)
    row = await db.get(OutreachDraftPolicy, tenant_id)
    now = utcnow_naive()
    before = _policy_dict(row) if row else None
    if row is None:
        row = OutreachDraftPolicy(tenant_id=tenant_id, created_at=now)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by, row.updated_at = actor.id, now
    db.add(row)
    db.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action="outreach.policy_updated",
            target_type="outreach_draft_policy",
            target_id=str(tenant_id),
            changes_json=json.dumps(
                {"before": before, "after": body.model_dump()}, default=str
            ),
        )
    )
    await db.commit()
    await db.refresh(row)
    return _policy_dict(row)


@router.get("/delivery-policies/{tenant_id}")
async def get_delivery_policy(tenant_id: uuid.UUID, db: DbDep, _: SuperuserDep):
    await _tenant(db, tenant_id)
    row = await db.get(OutreachDeliveryPolicy, tenant_id)
    return (
        _delivery_policy_dict(row)
        if row
        else _delivery_policy_dict(OutreachDeliveryPolicy(tenant_id=tenant_id), False)
    )


@router.put("/delivery-policies/{tenant_id}")
async def update_delivery_policy(
    tenant_id: uuid.UUID, body: DeliveryPolicyUpdate, db: DbDep, actor: SuperuserDep
):
    tenant = await _tenant(db, tenant_id)
    if body.mode == "approval_send" and not tenant_has_feature(tenant, "outreach_send"):
        raise HTTPException(
            status_code=409, detail="Enable the tenant outreach_send entitlement first"
        )
    row = await db.get(OutreachDeliveryPolicy, tenant_id)
    now = utcnow_naive()
    before = _delivery_policy_dict(row) if row else None
    if row is None:
        row = OutreachDeliveryPolicy(tenant_id=tenant_id, created_at=now)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    if body.controlled_auto_opt_in or body.controlled_auto_legal_approved:
        row.controlled_auto_reviewed_by = actor.id
        row.controlled_auto_reviewed_at = now
    row.updated_by, row.updated_at = actor.id, now
    db.add(row)
    db.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action="outreach.delivery_policy_updated",
            target_type="outreach_delivery_policy",
            target_id=str(tenant_id),
            changes_json=json.dumps(
                {"before": before, "after": body.model_dump()}, default=str
            ),
        )
    )
    await db.commit()
    await db.refresh(row)
    return _delivery_policy_dict(row)


@router.post("/candidates/{candidate_id}/enqueue")
async def enqueue_draft(candidate_id: uuid.UUID, db: DbDep, actor: SuperuserDep):
    candidate = await db.get(ContactCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Contact candidate not found")
    policy = await db.get(OutreachDraftPolicy, candidate.tenant_id)
    if not policy or policy.mode != "review_only":
        raise HTTPException(status_code=409, detail="Outreach drafting is off")
    job = enqueue_journey_summarize_job(
        db, tenant_id=candidate.tenant_id, candidate_id=candidate.id
    )
    _audit(
        db,
        actor,
        candidate.tenant_id,
        "outreach.draft_enqueued",
        candidate.id,
        {"job_id": str(job.id)},
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="A draft is already queued for this candidate today"
        ) from exc
    return {"job_id": str(job.id), "status": job.status}


@router.get("/messages")
async def list_messages(
    tenant_id: uuid.UUID,
    db: DbDep,
    _: SuperuserDep,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    await _tenant(db, tenant_id)
    query = (
        select(OutreachMessage)
        .where(OutreachMessage.tenant_id == tenant_id)
        .order_by(col(OutreachMessage.created_at).desc())
    )
    if status:
        query = query.where(OutreachMessage.status == status)
    rows = list((await db.exec(query.offset(offset).limit(limit))).all())
    snapshot_ids = {row.journey_snapshot_id for row in rows}
    snapshots = (
        list(
            (
                await db.exec(
                    select(JourneySnapshot).where(
                        col(JourneySnapshot.id).in_(snapshot_ids)
                    )
                )
            ).all()
        )
        if snapshot_ids
        else []
    )
    snapshot_map = {row.id: row for row in snapshots}
    return {
        "data": [
            _message_dict(row, snapshot_map.get(row.journey_snapshot_id))
            for row in rows
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get("/messages/{message_id}")
async def get_message(message_id: uuid.UUID, db: DbDep, _: SuperuserDep):
    row = await db.get(OutreachMessage, message_id)
    if not row:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    return _message_dict(row, await db.get(JourneySnapshot, row.journey_snapshot_id))


@router.post("/messages/{message_id}/revisions")
async def revise_message(
    message_id: uuid.UUID, body: DraftRevisionIn, db: DbDep, actor: SuperuserDep
):
    original = (
        await db.exec(
            select(OutreachMessage)
            .where(OutreachMessage.id == message_id)
            .with_for_update()
        )
    ).first()
    if not original:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if original.status not in {"pending_review", "rejected"}:
        raise HTTPException(
            status_code=409,
            detail="Only pending or rejected unsent drafts can be revised",
        )
    try:
        validate_content(subject=body.subject, body_without_cta=body.body_without_cta)
    except OutreachContentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    latest = int(
        (
            await db.exec(
                select(func.max(OutreachMessage.revision_no)).where(
                    OutreachMessage.tenant_id == original.tenant_id,
                    OutreachMessage.contact_candidate_id
                    == original.contact_candidate_id,
                )
            )
        ).one()
        or 0
    )
    if original.revision_no != latest:
        raise HTTPException(
            status_code=409, detail="Only the latest revision can be revised"
        )
    text_body = f"{body.body_without_cta.strip()}\n\n{canonical_cta(original.language)}"
    html_body = "".join(
        f"<p>{html.escape(part)}</p>" for part in text_body.split("\n\n")
    )
    digest = hashlib.sha256(
        f"{body.subject.strip()}\n{text_body}\n{html_body}".encode()
    ).hexdigest()
    now = utcnow_naive()
    if original.status == "pending_review":
        original.status = "cancelled"
        original.review_note = f"Superseded by revision {latest + 1}: {body.note}"
        original.updated_at = now
        db.add(original)
    revised = OutreachMessage(
        tenant_id=original.tenant_id,
        visitor_id=original.visitor_id,
        company_identification_id=original.company_identification_id,
        contact_candidate_id=original.contact_candidate_id,
        contact_id=original.contact_id,
        journey_snapshot_id=original.journey_snapshot_id,
        nurture_sequence_id=original.nurture_sequence_id,
        nurture_step_id=original.nurture_step_id,
        revision_of_id=original.id,
        revision_no=latest + 1,
        purpose=original.purpose,
        channel=original.channel,
        language=original.language,
        to_email_ciphertext=original.to_email_ciphertext,
        to_email_hash=original.to_email_hash,
        to_email_masked=original.to_email_masked,
        subject_snapshot=body.subject.strip(),
        html_snapshot=html_body,
        text_snapshot=text_body,
        personalization_evidence=original.personalization_evidence,
        knowledge_version=original.knowledge_version,
        prompt_version="human-revision-v1",
        policy_version=original.policy_version,
        generation_model="human-reviewed",
        content_hash=digest,
        status="pending_review",
        created_by=actor.id,
        generated_at=now,
        created_at=now,
    )
    db.add(revised)
    await db.flush()
    db.add(
        OutreachMessageReview(
            tenant_id=revised.tenant_id,
            outreach_message_id=revised.id,
            action="revised",
            actor_user_id=actor.id,
            note=body.note,
            diff_json={
                "from_message_id": str(original.id),
                "from_content_hash": original.content_hash,
                "to_content_hash": digest,
            },
            created_at=now,
        )
    )
    _audit(
        db,
        actor,
        revised.tenant_id,
        "outreach.revised",
        revised.id,
        {"from_message_id": str(original.id), "revision_no": revised.revision_no},
    )
    await db.commit()
    return _message_dict(
        revised, await db.get(JourneySnapshot, revised.journey_snapshot_id)
    )


@router.post("/messages/{message_id}/review")
async def review_message(
    message_id: uuid.UUID, body: DraftDecisionIn, db: DbDep, actor: SuperuserDep
):
    row = (
        await db.exec(
            select(OutreachMessage)
            .where(OutreachMessage.id == message_id)
            .with_for_update()
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Outreach draft not found")
    if row.status != "pending_review":
        raise HTTPException(
            status_code=409, detail="Only pending drafts can be reviewed"
        )
    latest = int(
        (
            await db.exec(
                select(func.max(OutreachMessage.revision_no)).where(
                    OutreachMessage.tenant_id == row.tenant_id,
                    OutreachMessage.contact_candidate_id == row.contact_candidate_id,
                )
            )
        ).one()
        or 0
    )
    if row.revision_no != latest:
        raise HTTPException(
            status_code=409, detail="Only the latest revision can be reviewed"
        )
    expected_hash = hashlib.sha256(
        f"{row.subject_snapshot}\n{row.text_snapshot}\n{row.html_snapshot}".encode()
    ).hexdigest()
    if expected_hash != row.content_hash:
        raise HTTPException(
            status_code=409, detail="Draft content integrity check failed"
        )
    now = utcnow_naive()
    if body.decision == "approve":
        try:
            snapshot = await validate_message_for_approval(db, row)
        except (OutreachDraftBlocked, OutreachContentError, ValueError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        row.status, row.approved_by, row.approved_at = "approved", actor.id, now
    else:
        snapshot = await db.get(JourneySnapshot, row.journey_snapshot_id)
        row.status, row.rejected_by, row.rejected_at = "rejected", actor.id, now
    row.review_note = body.note
    row.updated_at = now
    db.add(row)
    completed_action = "approved" if body.decision == "approve" else "rejected"
    db.add(
        OutreachMessageReview(
            tenant_id=row.tenant_id,
            outreach_message_id=row.id,
            action=completed_action,
            actor_user_id=actor.id,
            reason_code=body.reason_code,
            note=body.note,
            diff_json={"content_hash": row.content_hash},
            created_at=now,
        )
    )
    _audit(
        db,
        actor,
        row.tenant_id,
        f"outreach.{completed_action}",
        row.id,
        {"reason_code": body.reason_code, "send_enqueued": False},
    )
    await db.commit()
    return _message_dict(row, snapshot)


@router.post("/messages/{message_id}/send")
async def queue_message_send(
    message_id: uuid.UUID, body: DeliveryActionIn, db: DbDep, actor: SuperuserDep
):
    row = (
        await db.exec(
            select(OutreachMessage)
            .where(OutreachMessage.id == message_id)
            .with_for_update()
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Outreach message not found")
    if row.status == "queued":
        existing = (
            await db.exec(
                select(OperationalJob).where(
                    OperationalJob.idempotency_key
                    == f"outreach-send:{row.tenant_id}:{row.id}"
                )
            )
        ).first()
        return {
            "message": _message_dict(row),
            "job_id": str(existing.id) if existing else None,
            "duplicate": True,
        }
    if row.status != "approved" or not row.approved_by or not row.approved_at:
        raise HTTPException(
            status_code=409, detail="Only a human-approved message can be queued"
        )
    if (
        not settings.EMAIL_EXTERNAL_DELIVERY_ENABLED
        or not settings.OUTREACH_SEND_ENABLED
    ):
        raise HTTPException(
            status_code=409, detail="Platform outreach delivery kill switch is off"
        )
    if (
        not settings.RESEND_API_KEY.strip()
        or not settings.OUTREACH_PUBLIC_BASE_URL.strip().startswith(
            ("https://", "http://")
        )
        or (
            settings.is_production
            and not settings.OUTREACH_PUBLIC_BASE_URL.strip().startswith("https://")
        )
        or len(settings.OUTREACH_UNSUBSCRIBE_SECRET.strip()) < 32
        or not resend_webhook_signing_configured()
    ):
        raise HTTPException(
            status_code=409, detail="Platform outreach delivery is not fully configured"
        )
    tenant = await _tenant(db, row.tenant_id)
    policy = await db.get(OutreachDeliveryPolicy, row.tenant_id)
    if (
        not tenant_has_feature(tenant, "outreach_send")
        or not policy
        or policy.mode != "approval_send"
    ):
        raise HTTPException(
            status_code=409, detail="Tenant APPROVAL_SEND is not enabled"
        )
    try:
        await validate_message_for_approval(db, row)
    except (OutreachDraftBlocked, OutreachContentError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    latest = int(
        (
            await db.exec(
                select(func.max(OutreachMessage.revision_no)).where(
                    OutreachMessage.tenant_id == row.tenant_id,
                    OutreachMessage.contact_candidate_id == row.contact_candidate_id,
                )
            )
        ).one()
        or 0
    )
    if row.revision_no != latest:
        raise HTTPException(
            status_code=409, detail="Only the latest approved revision may be queued"
        )
    now = utcnow_naive()
    row.status = "queued"
    row.send_requested_by = actor.id
    row.send_requested_at = now
    row.send_idempotency_key = f"forgebase-outreach-{row.id}-{row.content_hash[:16]}"
    row.last_error = None
    row.updated_at = now
    db.add(row)
    job = enqueue_outreach_send_job(db, tenant_id=row.tenant_id, message_id=row.id)
    db.add(
        OutreachMessageReview(
            tenant_id=row.tenant_id,
            outreach_message_id=row.id,
            action="send_queued",
            actor_user_id=actor.id,
            note=body.note,
            diff_json={"content_hash": row.content_hash},
            created_at=now,
        )
    )
    _audit(
        db,
        actor,
        row.tenant_id,
        "outreach.send_queued",
        row.id,
        {"job_id": str(job.id), "content_hash": row.content_hash},
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="This message already has a send request"
        ) from exc
    return {"message": _message_dict(row), "job_id": str(job.id), "duplicate": False}


@router.post("/messages/{message_id}/cancel")
async def cancel_message_send(
    message_id: uuid.UUID, body: DeliveryActionIn, db: DbDep, actor: SuperuserDep
):
    row = (
        await db.exec(
            select(OutreachMessage)
            .where(OutreachMessage.id == message_id)
            .with_for_update()
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Outreach message not found")
    if row.status != "queued":
        raise HTTPException(
            status_code=409,
            detail="Only a queued, not-yet-sending message can be cancelled",
        )
    row.status, row.last_error = "cancelled", body.note or "Cancelled by operator"
    row.updated_at = utcnow_naive()
    job = (
        await db.exec(
            select(OperationalJob)
            .where(
                OperationalJob.idempotency_key
                == f"outreach-send:{row.tenant_id}:{row.id}"
            )
            .with_for_update()
        )
    ).first()
    if job and job.status in {"pending", "retry"}:
        job.status, job.last_error, job.updated_at = (
            "failed",
            "Cancelled by operator",
            utcnow_naive(),
        )
        db.add(job)
    db.add(row)
    db.add(
        OutreachMessageReview(
            tenant_id=row.tenant_id,
            outreach_message_id=row.id,
            action="send_cancelled",
            actor_user_id=actor.id,
            note=body.note,
            created_at=utcnow_naive(),
        )
    )
    _audit(
        db,
        actor,
        row.tenant_id,
        "outreach.send_cancelled",
        row.id,
        {"job_id": str(job.id) if job else None},
    )
    await db.commit()
    return _message_dict(row)


@router.post("/messages/{message_id}/retry")
async def retry_message_send(
    message_id: uuid.UUID, body: DeliveryActionIn, db: DbDep, actor: SuperuserDep
):
    row = (
        await db.exec(
            select(OutreachMessage)
            .where(OutreachMessage.id == message_id)
            .with_for_update()
        )
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Outreach message not found")
    if (
        row.status != "failed"
        or not row.sending_at
        or utcnow_naive() - row.sending_at >= timedelta(hours=23)
    ):
        raise HTTPException(
            status_code=409,
            detail="Retry is allowed only inside the provider idempotency window",
        )
    if row.provider_message_id:
        raise HTTPException(
            status_code=409, detail="Provider already accepted this message"
        )
    job = (
        await db.exec(
            select(OperationalJob)
            .where(
                OperationalJob.idempotency_key
                == f"outreach-send:{row.tenant_id}:{row.id}"
            )
            .with_for_update()
        )
    ).first()
    if not job:
        raise HTTPException(status_code=409, detail="Original send job was not found")
    row.status, row.last_error = "queued", None
    row.updated_at = utcnow_naive()
    job.status, job.attempts, job.available_at, job.locked_at, job.last_error = (
        "retry",
        0,
        utcnow_naive(),
        None,
        None,
    )
    db.add(row)
    db.add(job)
    db.add(
        OutreachMessageReview(
            tenant_id=row.tenant_id,
            outreach_message_id=row.id,
            action="send_retried",
            actor_user_id=actor.id,
            note=body.note,
            created_at=utcnow_naive(),
        )
    )
    _audit(
        db,
        actor,
        row.tenant_id,
        "outreach.send_retried",
        row.id,
        {"job_id": str(job.id)},
    )
    await db.commit()
    return {"message": _message_dict(row), "job_id": str(job.id)}


@router.get("/messages/{message_id}/events")
async def message_events(message_id: uuid.UUID, db: DbDep, _: SuperuserDep):
    row = await db.get(OutreachMessage, message_id)
    if not row:
        raise HTTPException(status_code=404, detail="Outreach message not found")
    events = list(
        (
            await db.exec(
                select(EmailDeliveryEvent)
                .where(EmailDeliveryEvent.outreach_message_id == message_id)
                .order_by(
                    col(EmailDeliveryEvent.occurred_at).asc(),
                    col(EmailDeliveryEvent.created_at).asc(),
                )
            )
        ).all()
    )
    return {
        "data": [
            {
                "id": str(event.id),
                "event_type": event.event_type,
                "reason_code": event.reason_code,
                "provider": event.provider,
                "provider_event_id": event.provider_event_id,
                "occurred_at": event.occurred_at.isoformat()
                if event.occurred_at
                else None,
                "created_at": event.created_at.isoformat(),
            }
            for event in events
        ]
    }


@public_router.get("/unsubscribe/{token}", response_class=HTMLResponse)
async def unsubscribe_confirmation(token: str, db: DbDep):
    try:
        claims = verify_unsubscribe_token(token)
    except InvalidUnsubscribeToken as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = await db.get(OutreachMessage, claims.message_id)
    if (
        not row
        or row.tenant_id != claims.tenant_id
        or row.to_email_hash != claims.email_hash
        or row.unsubscribe_token_hash != token_hash(token)
    ):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")
    return HTMLResponse(
        "<!doctype html><html><body><h1>Unsubscribe</h1><p>Confirm that you no longer want these business emails.</p><form method='post'><button type='submit'>Unsubscribe</button></form></body></html>"
    )


@public_router.post("/unsubscribe/{token}")
async def unsubscribe_one_click(token: str, db: DbDep):
    try:
        claims = verify_unsubscribe_token(token)
    except InvalidUnsubscribeToken as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    row = (
        await db.exec(
            select(OutreachMessage)
            .where(OutreachMessage.id == claims.message_id)
            .with_for_update()
        )
    ).first()
    digest = token_hash(token)
    if (
        not row
        or row.tenant_id != claims.tenant_id
        or row.to_email_hash != claims.email_hash
        or row.unsubscribe_token_hash != digest
    ):
        raise HTTPException(status_code=400, detail="Invalid unsubscribe token")
    event_id = f"forgebase:unsubscribe:{digest}"
    existing = (
        await db.exec(
            select(EmailDeliveryEvent.id).where(
                EmailDeliveryEvent.provider_event_id == event_id
            )
        )
    ).first()
    if existing:
        return {"unsubscribed": True, "duplicate": True}
    await record_suppression(
        db,
        tenant_id=row.tenant_id,
        email_digest=row.to_email_hash,
        email_masked=row.to_email_masked,
        scope=claims.scope,
        reason="unsubscribe",
        source_event_id=event_id,
    )
    cancelled = await cancel_queued_for_hash(
        db,
        email_digest=row.to_email_hash,
        tenant_id=None if claims.scope == "global" else row.tenant_id,
        reason="Recipient unsubscribed",
    )
    now = utcnow_naive()
    row.status, row.unsubscribed_at = "unsubscribed", now
    row.updated_at = now
    db.add(row)
    db.add(
        EmailDeliveryEvent(
            tenant_id=row.tenant_id,
            outreach_message_id=row.id,
            provider="forgebase",
            provider_event_id=event_id,
            provider_message_id=row.provider_message_id,
            event_type="email.unsubscribed",
            recipient_hash=row.to_email_hash,
            recipient_masked=row.to_email_masked,
            reason_code="one_click",
            event_data_json="{}",
            occurred_at=now,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        return {"unsubscribed": True, "duplicate": True}
    return {"unsubscribed": True, "duplicate": False, "cancelled_queued": cancelled}
