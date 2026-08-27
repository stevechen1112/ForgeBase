"""
RFQ API — 1b.4.4, 1b.4.5, 1b.4.6, 1b.4.8

POST /forms/rfq              — submit RFQ form (public, no auth)
GET  /tracking/rfqs          — list RFQs with filters (admin)
GET  /tracking/rfqs/{id}     — RFQ detail (admin)
PUT  /tracking/rfqs/{id}/status   — update status  (admin)
PUT  /tracking/rfqs/{id}/assign   — assign to sales user (admin)
"""
import csv
import io
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID as _UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from pydantic import Field as PydanticField
from sqlalchemy import text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette.responses import StreamingResponse

from app.api.v1.deps import (
    get_current_user,
    require_content_editor,
    require_rfq_manager,
    require_rfq_operator,
    resolve_tenant_id,
)
from app.core.config import settings
from app.core.datetime import isoformat_utc, utcnow_naive
from app.db.session import get_session
from app.models.application import Application
from app.models.contact import Contact
from app.models.product import Product
from app.models.reply_template import ReplyTemplate
from app.models.rfq_draft import RFQDraft
from app.models.rfq_event import RFQEvent
from app.models.rfq_note import RFQNote
from app.models.rfq_request import RFQProductLink, RFQRequest
from app.models.tracking_event import TrackingEvent
from app.models.user import User
from app.models.visitor import Visitor
from app.services.attribution import derive_attribution, record_outcome_change
from app.services.email_governance import is_authorized_synthetic_request
from app.services.form_challenge import (
    issue_form_challenge,
    validate_form_challenge,
    verify_turnstile,
)
from app.services.reply_quality import (
    build_reply_checklist,
    match_templates,
    quote_readiness,
    suggested_questions,
)

# Two routers — public forms_router + admin tracking_router
forms_router = APIRouter(prefix="/forms", tags=["Forms"])
tracking_router = APIRouter(prefix="/tracking", tags=["Tracking"])
logger = logging.getLogger(__name__)


async def _log_rfq_event(
    db: AsyncSession,
    rfq_id: uuid.UUID,
    event_type: str,
    summary: str,
    *,
    actor_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[uuid.UUID] = None,
    detail: Optional[str] = None,
) -> None:
    """Append an immutable event to the rfq_events audit log."""
    db.add(RFQEvent(
        rfq_id=rfq_id,
        tenant_id=tenant_id,
        actor_id=actor_id,
        event_type=event_type,
        summary=summary,
        detail=detail,
    ))

VALID_STATUSES = {"new", "assigned", "in_progress", "quoted", "negotiation", "won", "lost", "expired"}
VALID_PRIORITIES = {"normal", "high", "urgent"}

HOW_DID_YOU_FIND_VALUES = {
    "google", "linkedin", "trade_show", "referral",
    "direct", "email", "other",
}


# ── Public: RFQ Form submission ───────────────────────────────────────────────

class RFQFormIn(BaseModel):
    # Contact info
    full_name: str = PydanticField(min_length=2, max_length=100)
    email: EmailStr
    company_name: str = PydanticField(min_length=2, max_length=200)
    phone: Optional[str] = PydanticField(default=None, max_length=50)
    country: str = PydanticField(min_length=2, max_length=100)
    job_title: Optional[str] = PydanticField(default=None, max_length=100)

    # Product interest
    product_ids: List[str] = PydanticField(default_factory=list)
    application_id: Optional[str] = None
    quantity: Optional[str] = PydanticField(default=None, max_length=100)
    specifications: Optional[str] = PydanticField(default=None, max_length=4000)

    # Trade terms (optional step 2 — strong buyer signals, T10)
    incoterm: Optional[str] = None
    annual_volume: Optional[str] = PydanticField(default=None, max_length=100)
    is_trial_order: Optional[bool] = None
    required_certs: List[str] = PydanticField(default_factory=list)
    target_price: Optional[str] = PydanticField(default=None, max_length=100)

    # Request details
    timeline: Optional[str] = None
    message: Optional[str] = PydanticField(default=None, max_length=4000)
    how_did_you_find_us: Optional[str] = None
    consent: bool

    # Tracking
    visitor_id: Optional[str] = None    # client cookie UUID
    source_page: Optional[str] = PydanticField(default=None, max_length=500)
    draft_id: Optional[uuid.UUID] = None
    bot_challenge: Optional[str] = PydanticField(default=None, max_length=1000)
    turnstile_token: Optional[str] = PydanticField(default=None, max_length=2000)
    website: Optional[str] = PydanticField(default=None, max_length=200)  # honeypot

    @field_validator("full_name", "company_name", "country", "phone", "job_title", "quantity", "specifications", "annual_volume", "target_price", "message", "source_page")
    @classmethod
    def clean_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("how_did_you_find_us")
    @classmethod
    def validate_how(cls, v):
        if v and v not in HOW_DID_YOU_FIND_VALUES:
            raise ValueError("Invalid how_did_you_find_us value")
        return v

    @field_validator("product_ids", mode="before")
    @classmethod
    def limit_products(cls, v):
        if isinstance(v, list) and len(v) > 20:
            raise ValueError("Maximum 20 products per RFQ")
        return v

    @field_validator("timeline")
    @classmethod
    def validate_timeline(cls, v):
        valid = {"immediate", "1-3 months", "3-6 months", "evaluating"}
        if v and v not in valid:
            raise ValueError("Invalid timeline value")
        return v

    @field_validator("consent")
    @classmethod
    def validate_consent(cls, v):
        if v is not True:
            raise ValueError("consent must be accepted")
        return v

    @field_validator("incoterm")
    @classmethod
    def validate_incoterm(cls, v):
        if v:
            from app.services.rfq_quality import VALID_INCOTERMS
            v = v.strip().upper()
            if v not in VALID_INCOTERMS:
                raise ValueError("Invalid incoterm value")
        return v

    @field_validator("required_certs")
    @classmethod
    def limit_certs(cls, v):
        if isinstance(v, list) and len(v) > 10:
            raise ValueError("Maximum 10 certifications")
        return [c.strip()[:50] for c in v if c and c.strip()]


@forms_router.get("/rfq/challenge")
async def get_rfq_challenge(
    tenant_id: Optional[_UUID] = Depends(resolve_tenant_id),
):
    return {"challenge": issue_form_challenge(tenant_id), "turnstile_required": bool(settings.TURNSTILE_SECRET_KEY)}


@forms_router.post("/rfq", status_code=status.HTTP_201_CREATED)
async def submit_rfq(
    body: RFQFormIn,
    request: Request,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[_UUID] = Depends(resolve_tenant_id),
):
    """
    Submit RFQ form. Creates (or deduplicates) a Contact, then creates a
    new RFQRequest. Returns the generated RFQ number.
    Auto-sets priority=high when visitor intent score ≥ 30 (spec 12.7.5).
    """
    if body.website:
        raise HTTPException(status_code=422, detail="Form verification failed")
    is_test_data = is_authorized_synthetic_request(
        request.headers.get("x-forgebase-test-token")
    )
    test_run_id = (
        request.headers.get("x-forgebase-test-run", "")[:100] or None
    ) if is_test_data else None
    challenge_required = settings.is_production or settings.RFQ_BOT_CHALLENGE_REQUIRED
    if challenge_required and (not body.bot_challenge or not validate_form_challenge(body.bot_challenge, tenant_id)):
        raise HTTPException(status_code=422, detail="Form challenge is invalid or expired")
    remote_ip = request.client.host if request.client else None
    if not await verify_turnstile(body.turnstile_token, remote_ip):
        raise HTTPException(status_code=422, detail="Bot verification failed")

    visitor_id_parsed: Optional[uuid.UUID] = None
    if body.visitor_id:
        try:
            visitor_id_parsed = uuid.UUID(body.visitor_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid visitor_id") from exc

    application_id_parsed: Optional[uuid.UUID] = None
    if body.application_id:
        try:
            application_id_parsed = uuid.UUID(body.application_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid application_id") from exc

    draft: Optional[RFQDraft] = None
    if body.draft_id:
        draft_statement = select(RFQDraft).where(
            RFQDraft.id == body.draft_id,
            RFQDraft.tenant_id == tenant_id,
            RFQDraft.consumed_at.is_(None),
            RFQDraft.expires_at > utcnow_naive(),
        )
        # A handoff token is single-use. Lock it before any RFQ work so two
        # concurrent submits cannot both pass the consumed_at check.
        if db.get_bind().dialect.name == "postgresql":
            draft_statement = draft_statement.with_for_update()
        draft = (
            await db.exec(draft_statement)
        ).first()
        if not draft or (visitor_id_parsed and draft.visitor_id != visitor_id_parsed):
            raise HTTPException(status_code=422, detail="RFQ handoff draft is invalid or expired")
        visitor_id_parsed = draft.visitor_id

    visitor: Optional[Visitor] = None

    # ── 1. Resolve intent score ────────────────────────────────────────────
    intent_score = 0
    if visitor_id_parsed:
        visitor = await db.get(Visitor, visitor_id_parsed)
        if visitor and visitor.tenant_id != tenant_id:
            raise HTTPException(status_code=422, detail="visitor_id does not belong to this site")
        if visitor:
            intent_score = visitor.intent_score
        elif draft:
            # A valid draft always references a real visitor through its FK.
            raise HTTPException(status_code=422, detail="RFQ handoff visitor no longer exists")
        else:
            # Essential/session-only identity may not have a tracking record
            # when analytics consent was declined. RFQ submission must still
            # work; simply leave the RFQ unlinked from analytics.
            visitor_id_parsed = None

    if application_id_parsed:
        application = await db.get(Application, application_id_parsed)
        if not application or application.tenant_id not in (None, tenant_id) or application.status != "published":
            raise HTTPException(status_code=422, detail="application_id does not belong to this site")

    validated_product_ids: list[uuid.UUID] = []
    for raw_product_id in body.product_ids:
        try:
            product_id = uuid.UUID(raw_product_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid product_id") from exc
        product = await db.get(Product, product_id)
        if not product or product.tenant_id not in (None, tenant_id) or product.status != "published":
            raise HTTPException(status_code=422, detail="product_id does not belong to this site")
        if product_id not in validated_product_ids:
            validated_product_ids.append(product_id)

    # ── 2. Upsert Contact (dedup within this tenant only) ────────────────
    now = utcnow_naive()
    contact = (
        await db.exec(
            select(Contact).where(
                Contact.email == body.email,
                Contact.tenant_id == tenant_id,
            )
        )
    ).first()

    if contact:
        # Enrich missing fields
        if not contact.company_name and body.company_name:
            contact.company_name = body.company_name
        if not contact.phone and body.phone:
            contact.phone = body.phone
        if not contact.country and body.country:
            contact.country = body.country
        contact.updated_at = now
        db.add(contact)
    else:
        contact = Contact(
            email=body.email,
            full_name=body.full_name.strip()[:100],
            company_name=body.company_name,
            phone=body.phone,
            country=body.country,
            job_title=body.job_title,
            intent_score_at_creation=intent_score,
            how_did_you_find_us=body.how_did_you_find_us,
            source_page=body.source_page,
            tenant_id=tenant_id,
        )
        db.add(contact)

    await db.flush()  # get contact.id
    if visitor and visitor.contact_id != contact.id:
        visitor.contact_id = contact.id
        visitor.updated_at = now
        db.add(visitor)

    # ── 3. Generate sequential RFQ number ───────────────────────────────
    date_str = now.strftime("%Y%m%d")
    prefix = f"RFQ-{date_str}-"
    # Serialize number allocation across workers. The unique index remains the
    # final safety net, while this prevents the common count+1 race.
    if db.get_bind().dialect.name == "postgresql":
        await db.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": f"forgebase-rfq-{date_str}"},
        )
    latest_number = (
        await db.exec(
            select(RFQRequest.rfq_number)
            .where(col(RFQRequest.rfq_number).like(f"{prefix}%"))
            .order_by(col(RFQRequest.rfq_number).desc())
            .limit(1)
        )
    ).first()
    try:
        next_sequence = int(latest_number.rsplit("-", 1)[-1]) + 1 if latest_number else 1
    except (TypeError, ValueError):
        logger.error("Malformed RFQ number found for prefix %s: %r", prefix, latest_number)
        raise HTTPException(status_code=500, detail="RFQ number allocation failed")
    rfq_number = f"{prefix}{str(next_sequence).zfill(3)}"

    # ── 4. Determine priority ─────────────────────────────────────────
    priority = "normal"
    if intent_score >= 60:
        priority = "urgent"
    elif intent_score >= 30:
        priority = "high"

    # ── 4b. Lead Quality Score (T9, rule-based v1) ────────────────────
    from app.services.rfq_quality import score_rfq_quality
    quality_score, quality_reasons = score_rfq_quality(body)

    # ── 4c. Timezone-aware first-response SLA (T7) ────────────────────
    from app.services.sla import compute_sla
    buyer_tz, sla_due = await compute_sla(body.country, tenant_id, now, db)

    # ── 5. Create RFQRequest ─────────────────────────────────────────
    form_snapshot = json.dumps({
        "full_name": body.full_name,
        "company_name": body.company_name,
        "email": body.email,
        "phone": body.phone,
        "country": body.country,
        "job_title": body.job_title,
        "quantity": body.quantity,
        "specifications": body.specifications,
        "timeline": body.timeline,
        "message": body.message,
        "how_did_you_find_us": body.how_did_you_find_us,
        "consent": body.consent,
        "product_ids": [str(product_id) for product_id in validated_product_ids],
        "incoterm": body.incoterm,
        "annual_volume": body.annual_volume,
        "is_trial_order": body.is_trial_order,
        "required_certs": body.required_certs,
        "target_price": body.target_price,
    }, ensure_ascii=False)

    intent_snapshot = None
    attribution_snapshot = None
    if visitor:
        intent_snapshot = json.dumps({
            "score": visitor.intent_score,
            "stage": visitor.intent_stage,
            "facets": {
                "product_interest": visitor.facet_product_interest,
                "trust_validation": visitor.facet_trust_validation,
                "procurement_readiness": visitor.facet_procurement_readiness,
                "urgency": visitor.facet_urgency,
            },
            "captured_at": now.isoformat(),
        })
        latest_event = (
            await db.exec(
                select(TrackingEvent)
                .where(
                    TrackingEvent.visitor_id == visitor.visitor_id,
                    TrackingEvent.tenant_id == tenant_id,
                )
                .order_by(TrackingEvent.timestamp.desc())
                .limit(1)
            )
        ).first()
        if latest_event:
            attribution_snapshot = json.dumps({
                "traffic_source": latest_event.traffic_source,
                "campaign_id": latest_event.campaign_id,
                "referrer": latest_event.referrer,
                "landing_or_latest_page": latest_event.page_url,
                "locale": latest_event.locale,
                "captured_at": now.isoformat(),
            })

    rfq = RFQRequest(
        rfq_number=rfq_number,
        contact_id=contact.id,
        visitor_id=visitor_id_parsed,
        application_id=application_id_parsed,
        form_data=form_snapshot,
        intent_score_at_submit=intent_score,
        intent_snapshot_json=intent_snapshot,
        attribution_json=attribution_snapshot,
        source_chat_session_id=draft.chat_session_id if draft else None,
        source_draft_id=draft.id if draft else None,
        status="new",
        priority=priority,
        source_page=body.source_page,
        tenant_id=tenant_id,
        quality_score=quality_score,
        quality_reasons_json=json.dumps(quality_reasons, ensure_ascii=False),
        buyer_timezone=buyer_tz,
        sla_due_at=sla_due,
        incoterm=body.incoterm,
        annual_volume=body.annual_volume[:100] if body.annual_volume else None,
        is_trial_order=body.is_trial_order,
        required_certs_json=json.dumps(body.required_certs, ensure_ascii=False) if body.required_certs else None,
        target_price=body.target_price[:100] if body.target_price else None,
        is_test_data=is_test_data,
        test_run_id=test_run_id,
    )
    db.add(rfq)
    await db.flush()

    # ── 6. Link products of interest ────────────────────────────────
    for pid in validated_product_ids:
        db.add(RFQProductLink(rfq_id=rfq.id, product_id=pid))

    if draft:
        draft.consumed_at = now
        db.add(draft)

    # ── 6b. Log creation event ─────────────────────────────────────────
    await _log_rfq_event(
        db, rfq.id, "created",
        f"RFQ {rfq_number} submitted by {body.email}",
        tenant_id=tenant_id,
        detail=json.dumps({
            "priority": priority,
            "intent_score": intent_score,
            "quality_score": quality_score,
        }),
    )
    if tenant_id:
        await derive_attribution(db, rfq=rfq)

    from app.services.operational_outbox import enqueue_operational_job
    common_payload = {"rfq_id": str(rfq.id)}
    enqueue_operational_job(db, job_type="rfq_route", payload=common_payload,
                            idempotency_key=f"rfq:{rfq.id}:route", tenant_id=tenant_id)
    if not is_test_data:
        enqueue_operational_job(db, job_type="rfq_notify", payload=common_payload,
                                idempotency_key=f"rfq:{rfq.id}:notify", tenant_id=tenant_id)
        enqueue_operational_job(db, job_type="rfq_hubspot", payload=common_payload,
                                idempotency_key=f"rfq:{rfq.id}:hubspot", tenant_id=tenant_id)
        agentos_payload = {**common_payload, "tenant_id": str(tenant_id) if tenant_id else None}
        enqueue_operational_job(db, job_type="rfq_agentos", payload=agentos_payload,
                                idempotency_key=f"rfq:{rfq.id}:agentos", tenant_id=tenant_id)
        enqueue_operational_job(db, job_type="rfq_webhook", payload=common_payload,
                                idempotency_key=f"rfq:{rfq.id}:webhook", tenant_id=tenant_id)
    if tenant_id and not is_test_data:
        tenant_payload = {"rfq_id": str(rfq.id), "tenant_id": str(tenant_id)}
        enqueue_operational_job(db, job_type="rfq_copilot", payload=tenant_payload,
                                idempotency_key=f"rfq:{rfq.id}:copilot", tenant_id=tenant_id)
        enqueue_operational_job(db, job_type="rfq_auto_reply", payload=tenant_payload,
                                idempotency_key=f"rfq:{rfq.id}:auto-reply", tenant_id=tenant_id)

    await db.commit()

    return {
        "rfq_number": rfq_number,
        "rfq_id": str(rfq.id),
        "priority": priority,
        "is_test_data": is_test_data,
    }


# ── Admin: RFQ management ─────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = PydanticField(default=None, max_length=500)
    deal_amount: Optional[Decimal] = PydanticField(default=None, gt=0, max_digits=14, decimal_places=2)
    deal_currency: str = PydanticField(default="USD", min_length=3, max_length=3)
    # §6.3：won/lost 必須填成交／流失原因（供日後回寫 intent 權重）

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

    @field_validator("deal_currency")
    @classmethod
    def validate_currency(cls, v):
        currency = v.strip().upper()
        if not currency.isalpha():
            raise ValueError("deal_currency must be a three-letter currency code")
        return currency


class AssignUpdate(BaseModel):
    assigned_to: uuid.UUID
    priority: Optional[str] = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v):
        if v and v not in VALID_PRIORITIES:
            raise ValueError(f"priority must be one of {VALID_PRIORITIES}")
        return v


class FollowUpUpdate(BaseModel):
    first_response_at: Optional[datetime] = None
    quote_sent_at: Optional[datetime] = None
    next_follow_up_at: Optional[datetime] = None
    lost_reason: Optional[str] = PydanticField(default=None, max_length=500)


class NoteCreate(BaseModel):
    body: str = PydanticField(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def clean_body(cls, v):
        body = v.strip()
        if not body:
            raise ValueError("Note cannot be empty")
        return body


class SpamUpdate(BaseModel):
    is_spam: bool
    reason: Optional[str] = PydanticField(default=None, max_length=500)


class MergeUpdate(BaseModel):
    duplicate_rfq_id: uuid.UUID


def _ensure_tenant_scope(user: User) -> uuid.UUID:
    if not user.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context required")
    return user.tenant_id


def _ensure_rfq_access(rfq: RFQRequest, user: User, *, write: bool = False) -> None:
    # Legacy platform-admin records may be tenantless. Keep their access
    # limited to equally tenantless legacy RFQs; they must never cross into a
    # tenant's operational data. Normal tenant users still require an exact
    # tenant match.
    if user.tenant_id is None:
        if rfq.tenant_id is not None:
            raise HTTPException(status_code=404, detail="RFQ not found")
    elif rfq.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if user.role == "sales" and rfq.assigned_to != user.id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if write and user.role not in ("admin", "owner", "sales"):
        raise HTTPException(status_code=403, detail="RFQ operator access required")


async def _enrich_rfq_rows(db: AsyncSession, rows: list[RFQRequest]) -> list[dict]:
    contact_ids = {r.contact_id for r in rows if r.contact_id}
    assignee_ids = {r.assigned_to for r in rows if r.assigned_to}
    contacts = (
        (await db.exec(select(Contact).where(col(Contact.id).in_(contact_ids)))).all()
        if contact_ids else []
    )
    assignees = (
        (await db.exec(select(User).where(col(User.id).in_(assignee_ids)))).all()
        if assignee_ids else []
    )
    contact_map = {c.id: c for c in contacts}
    assignee_map = {u.id: u for u in assignees}
    result: list[dict] = []
    for rfq in rows:
        row = _rfq_row(rfq)
        contact = contact_map.get(rfq.contact_id)
        assignee = assignee_map.get(rfq.assigned_to)
        row["contact"] = {
            "full_name": contact.full_name,
            "company_name": contact.company_name,
            "email": contact.email,
            "country": contact.country,
        } if contact else None
        row["assigned_to_name"] = assignee.full_name if assignee else None
        result.append(row)
    return result


@tracking_router.get("/rfqs")
async def list_rfqs(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    view: str = "active",
    follow_up: Optional[str] = None,
    sort: Optional[str] = None,
    sla: Optional[str] = None,
    include_test_data: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    tenant_id = _ensure_tenant_scope(_)
    if view not in {"active", "spam", "merged", "all"}:
        raise HTTPException(status_code=422, detail="Invalid RFQ view")
    if follow_up not in {None, "due", "overdue", "today", "upcoming"}:
        raise HTTPException(status_code=422, detail="Invalid follow-up filter")

    # sort="quality": 品質 × SLA — 最該先回的單在最上面（T11）
    if sort == "quality":
        q = select(RFQRequest).order_by(
            col(RFQRequest.quality_score).desc(),
            col(RFQRequest.sla_due_at).asc(),
            col(RFQRequest.created_at).asc(),
        )
    else:
        q = select(RFQRequest).order_by(col(RFQRequest.created_at).desc())
    q = q.where(RFQRequest.tenant_id == tenant_id)
    if not include_test_data:
        q = q.where(RFQRequest.is_test_data.is_(False))
    if _.role == "sales":
        q = q.where(RFQRequest.assigned_to == _.id)
    elif assigned_to:
        q = q.where(RFQRequest.assigned_to == assigned_to)
    if view == "active":
        q = q.where(RFQRequest.is_spam.is_(False), RFQRequest.merged_into_rfq_id.is_(None))
    elif view == "spam":
        q = q.where(RFQRequest.is_spam.is_(True))
    elif view == "merged":
        q = q.where(RFQRequest.merged_into_rfq_id.is_not(None))
    if status:
        q = q.where(RFQRequest.status == status)
    if priority:
        q = q.where(RFQRequest.priority == priority)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.join(Contact, Contact.id == RFQRequest.contact_id, isouter=True).where(
            col(RFQRequest.rfq_number).ilike(term)
            | col(Contact.full_name).ilike(term)
            | col(Contact.company_name).ilike(term)
            | col(Contact.email).ilike(term)
        )
    now = utcnow_naive()
    if follow_up == "due":
        q = q.where(
            RFQRequest.next_follow_up_at.is_not(None),
            col(RFQRequest.next_follow_up_at) < now + timedelta(days=1),
            RFQRequest.status.not_in(("won", "lost", "expired")),
        )
    elif follow_up == "overdue":
        q = q.where(
            RFQRequest.next_follow_up_at.is_not(None),
            col(RFQRequest.next_follow_up_at) < now,
            RFQRequest.status.not_in(("won", "lost", "expired")),
        )
    elif follow_up == "today":
        q = q.where(
            RFQRequest.next_follow_up_at.is_not(None),
            col(RFQRequest.next_follow_up_at) >= now,
            col(RFQRequest.next_follow_up_at) < now + timedelta(days=1),
        )
    elif follow_up == "upcoming":
        q = q.where(RFQRequest.next_follow_up_at.is_not(None), col(RFQRequest.next_follow_up_at) >= now)
    if sla == "breached":
        q = q.where(RFQRequest.sla_breached == True)
    elif sla == "due_soon":
        q = q.where(
            RFQRequest.first_response_at.is_(None),
            RFQRequest.sla_due_at.is_not(None),
            col(RFQRequest.sla_due_at) <= utcnow_naive() + timedelta(hours=1),
        )
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    return await _enrich_rfq_rows(db, list(rows))


@tracking_router.get("/rfqs/export.csv")
async def export_rfqs_csv(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_rfq_manager),
):
    """Export tenant RFQs for management handoff or offline review."""
    tenant_id = _ensure_tenant_scope(current_user)
    q = (
        select(RFQRequest)
        .where(RFQRequest.tenant_id == tenant_id)
        .where(RFQRequest.is_test_data.is_(False))
        .order_by(col(RFQRequest.created_at).desc())
        .limit(5000)
    )
    if status:
        q = q.where(RFQRequest.status == status)
    rows = list((await db.exec(q)).all())
    enriched = await _enrich_rfq_rows(db, rows)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow([
        "RFQ Number", "Company", "Contact", "Email", "Country", "Status",
        "Owner", "Next Follow-up", "Deal Amount", "Currency", "Source Page",
        "Created At", "Spam", "Merged Into",
    ])
    for rfq, row in zip(rows, enriched):
        contact = row.get("contact") or {}
        writer.writerow([
            rfq.rfq_number,
            contact.get("company_name") or "",
            contact.get("full_name") or "",
            contact.get("email") or "",
            contact.get("country") or "",
            rfq.status,
            row.get("assigned_to_name") or "",
            isoformat_utc(rfq.next_follow_up_at) or "",
            str(rfq.deal_amount) if rfq.deal_amount is not None else "",
            rfq.deal_currency,
            rfq.source_page or "",
            rfq.created_at.isoformat(),
            "yes" if rfq.is_spam else "no",
            str(rfq.merged_into_rfq_id) if rfq.merged_into_rfq_id else "",
        ])
    filename = f"forgebase-rfqs-{utcnow_naive().date().isoformat()}.csv"
    return StreamingResponse(
        iter([buffer.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@tracking_router.get("/rfqs/stats")
async def rfq_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """首回時間與 SLA 達成率統計（T8）。

    注意：必須定義在 /rfqs/{rfq_id} 之前，否則 "stats" 會被當成 UUID 解析。
    """
    tenant_id = _ensure_tenant_scope(_)
    since = utcnow_naive() - timedelta(days=days)
    q = select(RFQRequest).where(
        col(RFQRequest.created_at) >= since,
        RFQRequest.tenant_id == tenant_id,
        RFQRequest.is_spam.is_(False),
        RFQRequest.merged_into_rfq_id.is_(None),
        RFQRequest.is_test_data.is_(False),
    )
    if _.role == "sales":
        q = q.where(RFQRequest.assigned_to == _.id)
    rows = (await db.exec(q)).all()

    def _naive(dt):
        # created_at（timestamptz）與 SLA 欄位（timestamp）時區感知不一致，統一歸一
        return dt.replace(tzinfo=None) if dt is not None and dt.tzinfo is not None else dt

    now = utcnow_naive()
    total = len(rows)

    responded_hours = sorted(
        (_naive(r.first_response_at) - _naive(r.created_at)).total_seconds() / 3600.0
        for r in rows
        if r.first_response_at
    )
    avg_first_response_hours = (
        round(sum(responded_hours) / len(responded_hours), 2) if responded_hours else None
    )
    median_first_response_hours = (
        round(responded_hours[len(responded_hours) // 2], 2) if responded_hours else None
    )

    sla_applicable = [r for r in rows if r.sla_due_at]
    sla_met = sum(
        1 for r in sla_applicable
        if r.first_response_at and _naive(r.first_response_at) <= _naive(r.sla_due_at)
    )
    sla_breached = sum(
        1 for r in sla_applicable
        if (r.first_response_at and _naive(r.first_response_at) > _naive(r.sla_due_at))
        or (not r.first_response_at and _naive(r.sla_due_at) < now)
    )
    sla_pending = len(sla_applicable) - sla_met - sla_breached
    sla_closed = sla_met + sla_breached
    sla_achievement_rate = round(sla_met / sla_closed, 4) if sla_closed else None

    status_counts: dict[str, int] = {}
    for r in rows:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    quality_scores = [r.quality_score for r in rows if r.quality_score]
    avg_quality = round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else None

    # 追蹤視圖指標（原 /dashboard/conversions 獨有，2026-08 併入 RFQ 列表頁）
    # 「待處理」採全量未結案單計算，不受上方 30 天窗口限制：
    # 超過 30 天未報價／未指派的單仍是營運待辦，不應從摘要消失。
    _OPEN_STATUSES = ("new", "assigned", "in_progress")
    q_open = select(RFQRequest).where(
        col(RFQRequest.status).in_(_OPEN_STATUSES),
        RFQRequest.tenant_id == tenant_id,
        RFQRequest.is_spam.is_(False),
        RFQRequest.merged_into_rfq_id.is_(None),
        RFQRequest.is_test_data.is_(False),
    )
    if _.role == "sales":
        q_open = q_open.where(RFQRequest.assigned_to == _.id)
    open_rows = (await db.exec(q_open)).all()
    unquoted = len(open_rows)
    unassigned = sum(1 for r in open_rows if not r.assigned_to)
    overdue_follow_ups = sum(
        1 for r in open_rows if r.next_follow_up_at and _naive(r.next_follow_up_at) < now
    )
    due_today = sum(
        1 for r in open_rows
        if r.next_follow_up_at
        and _naive(r.next_follow_up_at) >= now
        and _naive(r.next_follow_up_at) < now + timedelta(days=1)
    )

    return {
        "period_days": days,
        "total_rfqs": total,
        "responded": len(responded_hours),
        "avg_first_response_hours": avg_first_response_hours,
        "median_first_response_hours": median_first_response_hours,
        "sla_applicable": len(sla_applicable),
        "sla_met": sla_met,
        "sla_breached": sla_breached,
        "sla_pending": sla_pending,
        "sla_achievement_rate": sla_achievement_rate,
        "avg_quality_score": avg_quality,
        "status_counts": status_counts,
        "unquoted": unquoted,
        "unassigned": unassigned,
        "overdue_follow_ups": overdue_follow_ups,
        "due_today": due_today,
    }


# ── 回覆品質輔助（§5.4）：checklist／quote readiness／範本庫 ─────────────────

class TemplateIn(BaseModel):
    name: str = PydanticField(max_length=120)
    body: str
    product_line: Optional[str] = PydanticField(default=None, max_length=80)
    country: Optional[str] = PydanticField(default=None, max_length=2)
    locale: str = PydanticField(default="en", max_length=5)


class TemplateUpdate(BaseModel):
    name: Optional[str] = PydanticField(default=None, max_length=120)
    body: Optional[str] = None
    product_line: Optional[str] = PydanticField(default=None, max_length=80)
    country: Optional[str] = PydanticField(default=None, max_length=2)
    locale: Optional[str] = PydanticField(default=None, max_length=5)


def _template_row(t: ReplyTemplate) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "product_line": t.product_line,
        "country": t.country,
        "locale": t.locale,
        "body": t.body,
        "updated_at": t.updated_at.isoformat(),
    }


@tracking_router.get("/rfqs/templates")
async def list_reply_templates(
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(ReplyTemplate).order_by(col(ReplyTemplate.updated_at).desc())
    if _.tenant_id:
        q = q.where(ReplyTemplate.tenant_id == _.tenant_id)
    rows = (await db.exec(q)).all()
    return [_template_row(t) for t in rows]


@tracking_router.post("/rfqs/templates", status_code=201)
async def create_reply_template(
    body: TemplateIn,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    t = ReplyTemplate(tenant_id=_.tenant_id, **body.model_dump())
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _template_row(t)


@tracking_router.patch("/rfqs/templates/{template_id}")
async def update_reply_template(
    template_id: uuid.UUID,
    body: TemplateUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    t = await db.get(ReplyTemplate, template_id)
    if not t or (_.tenant_id and t.tenant_id != _.tenant_id):
        raise HTTPException(status_code=404, detail="Template not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    t.updated_at = utcnow_naive()
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return _template_row(t)


@tracking_router.delete("/rfqs/templates/{template_id}", status_code=204)
async def delete_reply_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    t = await db.get(ReplyTemplate, template_id)
    if not t or (_.tenant_id and t.tenant_id != _.tenant_id):
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(t)
    await db.commit()


@tracking_router.get("/rfqs/{rfq_id}/reply-assist")
async def get_reply_assist(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """回覆前 checklist＋Quote Readiness＋建議反問＋匹配範本（§5.4）。"""
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(r, _)

    buyer_country = None
    if r.contact_id:
        contact = await db.get(Contact, r.contact_id)
        if contact:
            buyer_country = contact.country

    tq = select(ReplyTemplate)
    if _.tenant_id:
        tq = tq.where(ReplyTemplate.tenant_id == _.tenant_id)
    templates = (await db.exec(tq)).all()
    matched = match_templates(list(templates), country=buyer_country)[:3]

    return {
        "rfq_id": str(r.id),
        "checklist": build_reply_checklist(r),
        "quote_readiness": quote_readiness(r),
        "suggested_questions": suggested_questions(r),
        "templates": [_template_row(t) for t in matched],
        "buyer_country": buyer_country,
    }


@tracking_router.get("/rfqs/{rfq_id}")
async def get_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(r, _)

    # Fetch linked product IDs
    product_links = (
        await db.exec(
            select(RFQProductLink).where(RFQProductLink.rfq_id == rfq_id)
        )
    ).all()

    products = (
        await db.exec(
            select(Product)
            .join(RFQProductLink, RFQProductLink.product_id == Product.id)
            .where(RFQProductLink.rfq_id == rfq_id)
        )
    ).all()
    contact = await db.get(Contact, r.contact_id) if r.contact_id else None
    assignee = await db.get(User, r.assigned_to) if r.assigned_to else None

    visitor_events: list[TrackingEvent] = []
    if r.visitor_id:
        visitor_events = list((await db.exec(
            select(TrackingEvent)
            .where(
                TrackingEvent.visitor_id == r.visitor_id,
                TrackingEvent.tenant_id == r.tenant_id,
            )
            .order_by(col(TrackingEvent.timestamp).desc())
            .limit(20)
        )).all())

    duplicates: list[RFQRequest] = []
    if r.contact_id:
        duplicates = list((await db.exec(
            select(RFQRequest)
            .where(
                RFQRequest.contact_id == r.contact_id,
                RFQRequest.tenant_id == r.tenant_id,
                RFQRequest.id != r.id,
                RFQRequest.merged_into_rfq_id.is_(None),
            )
            .order_by(col(RFQRequest.created_at).desc())
            .limit(5)
        )).all())

    data = _rfq_row(r, full=True)
    data["product_ids"] = [str(pl.product_id) for pl in product_links]
    data["products"] = [
        {"id": str(p.id), "name": p.product_name, "model_number": p.model_number}
        for p in products
    ]
    data["contact"] = {
        "id": str(contact.id),
        "full_name": contact.full_name,
        "company_name": contact.company_name,
        "email": contact.email,
        "phone": contact.phone,
        "country": contact.country,
        "job_title": contact.job_title,
    } if contact else None
    data["assigned_to_name"] = assignee.full_name if assignee else None
    data["visitor_history"] = [
        {
            "event_name": event.event_name,
            "timestamp": event.timestamp.isoformat(),
            "page_url": event.page_url,
            "page_type": event.page_type,
            "traffic_source": event.traffic_source,
            "campaign_id": event.campaign_id,
            "locale": event.locale,
            "score_delta": event.score_delta,
        }
        for event in visitor_events
    ]
    data["duplicate_candidates"] = [
        {
            "id": str(item.id),
            "rfq_number": item.rfq_number,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
        }
        for item in duplicates
    ]
    data["crm_sync"] = {
        "hubspot": {
            "status": "linked" if r.hubspot_deal_id else "not_linked",
            "external_id": r.hubspot_deal_id,
        },
        "salesforce": {"status": "not_configured", "external_id": None},
    }
    return data


@tracking_router.put("/rfqs/{rfq_id}/status")
async def update_rfq_status(
    rfq_id: uuid.UUID,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_rfq_operator),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(r, _, write=True)
    old_status = r.status

    # §6.3：成交／流失原因必填
    if body.status in ("won", "lost"):
        existing_reason = r.won_reason if body.status == "won" else r.lost_reason
        if not (body.reason and body.reason.strip()) and not existing_reason:
            raise HTTPException(
                status_code=422,
                detail=f"reason is required when closing as {body.status}（成交／流失原因為必填，供漏斗分析與 intent 權重回寫）",
            )
        if body.reason and body.reason.strip():
            if body.status == "won":
                r.won_reason = body.reason.strip()
            else:
                r.lost_reason = body.reason.strip()
    if body.status == "won" and body.deal_amount is not None:
        r.deal_amount = body.deal_amount
        r.deal_currency = body.deal_currency

    r.status = body.status
    r.updated_at = utcnow_naive()
    # 僅真實跟進狀態記首回；lost/expired 不算回覆（避免 SLA／首回統計偏樂觀）
    _FIRST_RESPONSE_STATUSES = {"assigned", "in_progress", "quoted", "negotiation"}
    if old_status == "new" and body.status in _FIRST_RESPONSE_STATUSES and r.first_response_at is None:
        r.first_response_at = r.updated_at
    if body.status == "quoted" and r.quote_sent_at is None:
        # 漏斗量測：首次進入 quoted 視為報價送出（§6.3）
        r.quote_sent_at = r.updated_at
    if body.status in ("won", "lost", "expired"):
        r.closed_at = r.updated_at
        r.next_follow_up_at = None
    else:
        r.closed_at = None
    db.add(r)

    await _log_rfq_event(
        db, r.id, "status_changed",
        f"Status changed from {old_status} to {body.status}",
        actor_id=_.id, tenant_id=r.tenant_id,
        detail=json.dumps({
            "old_status": old_status,
            "new_status": body.status,
            "reason": body.reason.strip() if body.reason else None,
            "deal_amount": str(r.deal_amount) if body.status == "won" and r.deal_amount is not None else None,
            "deal_currency": r.deal_currency if body.status == "won" else None,
        }),
    )
    await record_outcome_change(
        db,
        rfq=r,
        previous_status=old_status,
        actor_user_id=_.id,
    )
    await db.commit()

    # 1b.5.3 Fire rfq.status_changed webhook
    try:
        from app.services.webhook import fire_webhook
        fire_webhook("rfq.status_changed", {
            "rfq_id":     str(r.id),
            "rfq_number": r.rfq_number,
            "old_status": old_status,
            "new_status": r.status,
        })
    except Exception:
        logger.warning("rfq.status_changed webhook failed", exc_info=True)

    return {
        "rfq_number": r.rfq_number,
        "status": r.status,
        "deal_amount": str(r.deal_amount) if r.deal_amount is not None else None,
        "deal_currency": r.deal_currency,
    }


@tracking_router.put("/rfqs/{rfq_id}/assign")
async def assign_rfq(
    rfq_id: uuid.UUID,
    body: AssignUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_rfq_manager),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(r, current_user, write=True)
    assignee = await db.get(User, body.assigned_to)
    if (
        not assignee
        or not assignee.is_active
        or assignee.tenant_id != current_user.tenant_id
        or assignee.role not in ("sales", "admin", "owner")
    ):
        raise HTTPException(status_code=422, detail="Assignee must be an active sales or manager user in this tenant")
    old_assigned = r.assigned_to
    r.assigned_to = body.assigned_to
    if body.priority:
        r.priority = body.priority
    if r.status == "new":
        r.status = "assigned"
    r.assigned_notified_at = None  # reset so notification fires again
    r.updated_at = utcnow_naive()
    db.add(r)

    summary_parts = [f"指派給 {assignee.full_name}"]
    if body.priority:
        summary_parts.append(f"priority set to {body.priority}")
    await _log_rfq_event(
        db, r.id, "assigned",
        "; ".join(summary_parts),
        actor_id=current_user.id, tenant_id=r.tenant_id,
        detail=json.dumps({
            "old_assigned_to": str(old_assigned) if old_assigned else None,
            "new_assigned_to": str(body.assigned_to),
            "priority": body.priority,
        }),
    )
    await db.commit()

    # Trigger assignment notification
    try:
        import asyncio

        from app.services.notifications import notify_rfq_assigned
        asyncio.create_task(notify_rfq_assigned(r.id))
    except Exception:
        logger.warning("rfq assign notification failed", exc_info=True)

    return {"rfq_number": r.rfq_number, "status": r.status, "assigned_to": str(r.assigned_to)}


@tracking_router.put("/rfqs/{rfq_id}/follow-up")
async def update_rfq_follow_up(
    rfq_id: uuid.UUID,
    body: FollowUpUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_rfq_operator),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(r, _, write=True)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        # Columns are TIMESTAMP WITHOUT TIME ZONE; strip tzinfo from aware inputs.
        if isinstance(value, datetime) and value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
            updates[field] = value
        setattr(r, field, value)
    r.updated_at = utcnow_naive()
    db.add(r)

    for field in updates:
        event_type_map = {
            "first_response_at": "first_response",
            "quote_sent_at": "quote_sent",
            "next_follow_up_at": "next_follow_up_set",
            "lost_reason": "lost_reason_set",
        }
        etype = event_type_map.get(field, field)
        val = updates[field]
        await _log_rfq_event(
            db, r.id, etype,
            (
                "已設定下次跟進時間" if field == "next_follow_up_at"
                else f"{field} recorded" if field != "lost_reason"
                else f"Lost reason: {val}"
            ),
            actor_id=_.id, tenant_id=r.tenant_id,
            detail=json.dumps({"field": field, "value": val.isoformat() if isinstance(val, datetime) else val}),
        )

    await db.commit()
    return {"rfq_number": r.rfq_number, "updated_fields": list(updates.keys())}


@tracking_router.get("/rfqs/{rfq_id}/notes")
async def list_rfq_notes(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(rfq, _)
    rows = list((await db.exec(
        select(RFQNote)
        .where(RFQNote.rfq_id == rfq_id, RFQNote.tenant_id == rfq.tenant_id)
        .order_by(col(RFQNote.created_at).desc())
    )).all())
    author_ids = {note.author_id for note in rows}
    authors = list((await db.exec(select(User).where(col(User.id).in_(author_ids)))).all()) if author_ids else []
    author_map = {user.id: user.full_name for user in authors}
    return [
        {
            "id": str(note.id),
            "body": note.body,
            "author_id": str(note.author_id),
            "author_name": author_map.get(note.author_id, "已停用使用者"),
            "created_at": note.created_at.isoformat(),
        }
        for note in rows
    ]


@tracking_router.post("/rfqs/{rfq_id}/notes", status_code=201)
async def create_rfq_note(
    rfq_id: uuid.UUID,
    body: NoteCreate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_rfq_operator),
):
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(rfq, _, write=True)
    note = RFQNote(
        tenant_id=rfq.tenant_id,
        rfq_id=rfq.id,
        author_id=_.id,
        body=body.body,
    )
    db.add(note)
    await _log_rfq_event(
        db,
        rfq.id,
        "note_added",
        f"{_.full_name} 新增內部備註",
        actor_id=_.id,
        tenant_id=rfq.tenant_id,
        detail=json.dumps({"note_id": str(note.id)}),
    )
    await db.commit()
    await db.refresh(note)
    return {
        "id": str(note.id),
        "body": note.body,
        "author_id": str(note.author_id),
        "author_name": _.full_name,
        "created_at": note.created_at.isoformat(),
    }


@tracking_router.put("/rfqs/{rfq_id}/spam")
async def update_rfq_spam(
    rfq_id: uuid.UUID,
    body: SpamUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_rfq_operator),
):
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(rfq, _, write=True)
    if body.is_spam and not (body.reason and body.reason.strip()):
        raise HTTPException(status_code=422, detail="reason is required when marking spam")
    rfq.is_spam = body.is_spam
    rfq.spam_reason = body.reason.strip() if body.is_spam and body.reason else None
    rfq.spam_marked_at = utcnow_naive() if body.is_spam else None
    rfq.spam_marked_by = _.id if body.is_spam else None
    rfq.updated_at = utcnow_naive()
    db.add(rfq)
    await _log_rfq_event(
        db,
        rfq.id,
        "spam_marked" if body.is_spam else "spam_restored",
        "移至垃圾詢價隔離區" if body.is_spam else "從垃圾詢價隔離區還原",
        actor_id=_.id,
        tenant_id=rfq.tenant_id,
        detail=json.dumps({"reason": rfq.spam_reason}),
    )
    await db.commit()
    return {"rfq_number": rfq.rfq_number, "is_spam": rfq.is_spam}


@tracking_router.post("/rfqs/{rfq_id}/merge")
async def merge_duplicate_rfq(
    rfq_id: uuid.UUID,
    body: MergeUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_rfq_manager),
):
    primary = await db.get(RFQRequest, rfq_id)
    duplicate = await db.get(RFQRequest, body.duplicate_rfq_id)
    if not primary or not duplicate:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(primary, _, write=True)
    _ensure_rfq_access(duplicate, _, write=True)
    if primary.id == duplicate.id:
        raise HTTPException(status_code=422, detail="Cannot merge an RFQ into itself")
    if duplicate.merged_into_rfq_id:
        raise HTTPException(status_code=409, detail="Duplicate RFQ has already been merged")
    duplicate.merged_into_rfq_id = primary.id
    duplicate.merged_at = utcnow_naive()
    duplicate.updated_at = duplicate.merged_at
    db.add(duplicate)
    detail = json.dumps({"primary_rfq_id": str(primary.id), "duplicate_rfq_id": str(duplicate.id)})
    await _log_rfq_event(
        db, primary.id, "duplicate_merged", f"合併重複詢價 {duplicate.rfq_number}",
        actor_id=_.id, tenant_id=primary.tenant_id, detail=detail,
    )
    await _log_rfq_event(
        db, duplicate.id, "merged_into", f"已合併至 {primary.rfq_number}",
        actor_id=_.id, tenant_id=duplicate.tenant_id, detail=detail,
    )
    await db.commit()
    return {"primary_rfq_id": str(primary.id), "merged_rfq_id": str(duplicate.id)}


@tracking_router.get("/rfqs/{rfq_id}/events")
async def list_rfq_events(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Return the full event timeline for a single RFQ, newest first."""
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    _ensure_rfq_access(r, _)

    rows = (
        await db.exec(
            select(RFQEvent)
            .where(RFQEvent.rfq_id == rfq_id)
            .order_by(col(RFQEvent.created_at).desc())
        )
    ).all()
    actor_ids = {event.actor_id for event in rows if event.actor_id}
    actors = list((await db.exec(select(User).where(col(User.id).in_(actor_ids)))).all()) if actor_ids else []
    actor_map = {actor.id: actor.full_name for actor in actors}

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "summary": e.summary,
            "detail": json.loads(e.detail) if e.detail else None,
            "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_name": actor_map.get(e.actor_id),
            "created_at": e.created_at.isoformat(),
        }
        for e in rows
    ]


# ── Helper ────────────────────────────────────────────────────────────────────

def _rfq_row(r: RFQRequest, full: bool = False) -> dict:
    base = {
        "id": str(r.id),
        "rfq_number": r.rfq_number,
        "contact_id": str(r.contact_id) if r.contact_id else None,
        "visitor_id": str(r.visitor_id) if r.visitor_id else None,
        "status": r.status,
        "priority": r.priority,
        "intent_score_at_submit": r.intent_score_at_submit,
        "quality_score": r.quality_score,
        "sla_due_at": r.sla_due_at.isoformat() if r.sla_due_at else None,
        "sla_breached": r.sla_breached,
        "assigned_to": str(r.assigned_to) if r.assigned_to else None,
        "next_follow_up_at": isoformat_utc(r.next_follow_up_at),
        "is_spam": r.is_spam,
        "spam_reason": r.spam_reason,
        "merged_into_rfq_id": str(r.merged_into_rfq_id) if r.merged_into_rfq_id else None,
        "deal_amount": str(r.deal_amount) if r.deal_amount is not None else None,
        "deal_currency": r.deal_currency,
        "source_page": r.source_page,
        "created_at": r.created_at.isoformat(),
    }
    if full:
        base["application_id"] = str(r.application_id) if r.application_id else None
        base["source_page"] = r.source_page
        base["buyer_timezone"] = r.buyer_timezone
        base["hubspot_deal_id"] = r.hubspot_deal_id
        base["form_data"] = json.loads(r.form_data) if r.form_data else None
        base["quality_reasons"] = (
            json.loads(r.quality_reasons_json) if r.quality_reasons_json else []
        )
        base["incoterm"] = r.incoterm
        base["annual_volume"] = r.annual_volume
        base["is_trial_order"] = r.is_trial_order
        base["required_certs"] = (
            json.loads(r.required_certs_json) if r.required_certs_json else []
        )
        base["target_price"] = r.target_price
        base["assigned_notified_at"] = (
            r.assigned_notified_at.isoformat() if r.assigned_notified_at else None
        )
        base["reminder_24h_sent_at"] = (
            r.reminder_24h_sent_at.isoformat() if r.reminder_24h_sent_at else None
        )
        base["escalation_48h_sent_at"] = (
            r.escalation_48h_sent_at.isoformat() if r.escalation_48h_sent_at else None
        )
        base["closed_at"] = r.closed_at.isoformat() if r.closed_at else None
        base["updated_at"] = r.updated_at.isoformat()
        base["first_response_at"] = (
            r.first_response_at.isoformat() if r.first_response_at else None
        )
        base["quote_sent_at"] = (
            r.quote_sent_at.isoformat() if r.quote_sent_at else None
        )
        base["lost_reason"] = r.lost_reason
        base["won_reason"] = r.won_reason
        base["spam_marked_at"] = r.spam_marked_at.isoformat() if r.spam_marked_at else None
        base["merged_at"] = r.merged_at.isoformat() if r.merged_at else None
        base["agent_run_id"] = r.agent_run_id
        base["agent_analysis_summary"] = r.agent_analysis_summary
        base["agent_draft_body"] = r.agent_draft_body
    return base
