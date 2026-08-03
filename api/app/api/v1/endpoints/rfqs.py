"""
RFQ API — 1b.4.4, 1b.4.5, 1b.4.6, 1b.4.8

POST /forms/rfq              — submit RFQ form (public, no auth)
GET  /tracking/rfqs          — list RFQs with filters (admin)
GET  /tracking/rfqs/{id}     — RFQ detail (admin)
PUT  /tracking/rfqs/{id}/status   — update status  (admin)
PUT  /tracking/rfqs/{id}/assign   — assign to sales user (admin)
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field as PydanticField, field_validator
from sqlmodel import select, col, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor, resolve_tenant_id
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.contact import Contact
from app.models.reply_template import ReplyTemplate
from app.models.rfq_request import RFQRequest, RFQProductLink
from app.models.rfq_event import RFQEvent
from app.models.visitor import Visitor
from app.models.user import User
from app.services.reply_quality import (
    build_reply_checklist,
    match_templates,
    quote_readiness,
    suggested_questions,
)
from uuid import UUID as _UUID

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
    full_name: str
    email: EmailStr
    company_name: str
    phone: Optional[str] = None
    country: str
    job_title: Optional[str] = None

    # Product interest
    product_ids: List[str] = []          # UUID strings
    application_id: Optional[str] = None
    quantity: Optional[str] = None
    specifications: Optional[str] = None

    # Trade terms (optional step 2 — strong buyer signals, T10)
    incoterm: Optional[str] = None
    annual_volume: Optional[str] = None
    is_trial_order: Optional[bool] = None
    required_certs: List[str] = []
    target_price: Optional[str] = None

    # Request details
    timeline: Optional[str] = None
    message: Optional[str] = None
    how_did_you_find_us: Optional[str] = None
    consent: bool

    # Tracking
    visitor_id: Optional[str] = None    # client cookie UUID
    source_page: Optional[str] = None

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


@forms_router.post("/rfq", status_code=status.HTTP_201_CREATED)
async def submit_rfq(
    body: RFQFormIn,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[_UUID] = Depends(resolve_tenant_id),
):
    """
    Submit RFQ form. Creates (or deduplicates) a Contact, then creates a
    new RFQRequest. Returns the generated RFQ number.
    Auto-sets priority=high when visitor intent score ≥ 30 (spec 12.7.5).
    """
    visitor_id_parsed: Optional[uuid.UUID] = None
    if body.visitor_id:
        try:
            visitor_id_parsed = uuid.UUID(body.visitor_id)
        except ValueError:
            pass

    application_id_parsed: Optional[uuid.UUID] = None
    if body.application_id:
        try:
            application_id_parsed = uuid.UUID(body.application_id)
        except ValueError:
            pass

    # ── 1. Resolve intent score ────────────────────────────────────────────
    intent_score = 0
    if visitor_id_parsed:
        v = await db.get(Visitor, visitor_id_parsed)
        if v:
            intent_score = v.intent_score

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
        if not contact.visitor_id and visitor_id_parsed:
            contact.visitor_id = visitor_id_parsed
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
            visitor_id=visitor_id_parsed,
            intent_score_at_creation=intent_score,
            how_did_you_find_us=body.how_did_you_find_us,
            source_page=body.source_page,
            tenant_id=tenant_id,
        )
        db.add(contact)

    await db.flush()  # get contact.id

    # ── 3. Generate sequential RFQ number ───────────────────────────────
    date_str = now.strftime("%Y%m%d")
    prefix = f"RFQ-{date_str}-"
    count_result = await db.exec(
        select(func.count(RFQRequest.id)).where(
            col(RFQRequest.rfq_number).like(f"{prefix}%")
        )
    )
    day_count = count_result.one()
    rfq_number = f"{prefix}{str(day_count + 1).zfill(3)}"

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
        "product_ids": body.product_ids,
        "incoterm": body.incoterm,
        "annual_volume": body.annual_volume,
        "is_trial_order": body.is_trial_order,
        "required_certs": body.required_certs,
        "target_price": body.target_price,
    }, ensure_ascii=False)

    rfq = RFQRequest(
        rfq_number=rfq_number,
        contact_id=contact.id,
        visitor_id=visitor_id_parsed,
        application_id=application_id_parsed,
        form_data=form_snapshot,
        intent_score_at_submit=intent_score,
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
    )
    db.add(rfq)
    await db.flush()

    # ── 6. Link products of interest ────────────────────────────────
    for pid_str in body.product_ids:
        try:
            pid = uuid.UUID(pid_str)
        except ValueError:
            continue
        db.add(RFQProductLink(rfq_id=rfq.id, product_id=pid))

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

    await db.commit()

    # ── 7. Trigger routing + notification + HubSpot + webhook (async, non-blocking)
    # Imported inline to avoid circular dependency at module load time
    try:
        from app.services.rfq_routing import route_rfq
        from app.services.notifications import notify_new_rfq
        from app.services.hubspot import sync_rfq_to_hubspot
        from app.services.webhook import fire_webhook
        from app.services.agentOS import trigger_agentOS_rfq
        import asyncio
        from app.services.copilot import on_new_rfq as _copilot_on_rfq
        
        # Condition 1: Trigger AgentOS workflow (await to ensure agent_run_id is stored before response)
        try:
            await trigger_agentOS_rfq(rfq.id, tenant_id)
        except Exception:
            logger.warning("agentOS trigger failed (non-blocking)", exc_info=True)
        
        # Standard routing + notifications (background)
        asyncio.create_task(route_rfq(rfq.id))
        asyncio.create_task(notify_new_rfq(rfq.id))
        asyncio.create_task(sync_rfq_to_hubspot(rfq.id))
        if tenant_id:
            asyncio.create_task(_copilot_on_rfq(rfq.id, tenant_id))
            # T6: 自動專業確認信（per-tenant 開關，低品質不發）
            from app.services.rfq_auto_reply import maybe_auto_reply
            asyncio.create_task(maybe_auto_reply(rfq.id, tenant_id))
        fire_webhook("rfq.created", {
            "rfq_id":      str(rfq.id),
            "rfq_number":  rfq_number,
            "contact": {
                "full_name":    body.full_name,
                "email":        body.email,
                "company_name": body.company_name,
                "country":      body.country,
            },
            "products":    [{"product_id": pid} for pid in body.product_ids],
            "intent_score": intent_score,
            "priority":     priority,
            "source_page":  body.source_page,
        })
    except Exception:
        logger.warning("rfq routing/webhook failed", exc_info=True)  # routing failures must not block form submission

    return {
        "rfq_number": rfq_number,
        "rfq_id": str(rfq.id),
        "priority": priority,
    }


# ── Admin: RFQ management ─────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = PydanticField(default=None, max_length=500)
    # §6.3：won/lost 必須填成交／流失原因（供日後回寫 intent 權重）

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


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
    lost_reason: Optional[str] = PydanticField(default=None, max_length=500)


@tracking_router.get("/rfqs")
async def list_rfqs(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[uuid.UUID] = None,
    sort: Optional[str] = None,
    sla: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    # sort="quality": 品質 × SLA — 最該先回的單在最上面（T11）
    if sort == "quality":
        q = select(RFQRequest).order_by(
            col(RFQRequest.quality_score).desc(),
            col(RFQRequest.sla_due_at).asc(),
            col(RFQRequest.created_at).asc(),
        )
    else:
        q = select(RFQRequest).order_by(col(RFQRequest.created_at).desc())
    if _.tenant_id:
        q = q.where(RFQRequest.tenant_id == _.tenant_id)
    if status:
        q = q.where(RFQRequest.status == status)
    if priority:
        q = q.where(RFQRequest.priority == priority)
    if assigned_to:
        q = q.where(RFQRequest.assigned_to == assigned_to)
    if sla == "breached":
        q = q.where(RFQRequest.sla_breached == True)  # noqa: E712
    elif sla == "due_soon":
        q = q.where(
            RFQRequest.first_response_at.is_(None),
            RFQRequest.sla_due_at.is_not(None),
            col(RFQRequest.sla_due_at) <= utcnow_naive() + timedelta(hours=1),
        )
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    return [_rfq_row(r) for r in rows]


@tracking_router.get("/rfqs/stats")
async def rfq_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """首回時間與 SLA 達成率統計（T8）。

    注意：必須定義在 /rfqs/{rfq_id} 之前，否則 "stats" 會被當成 UUID 解析。
    """
    since = utcnow_naive() - timedelta(days=days)
    q = select(RFQRequest).where(col(RFQRequest.created_at) >= since)
    if _.tenant_id:
        q = q.where(RFQRequest.tenant_id == _.tenant_id)
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
    q_open = select(RFQRequest).where(col(RFQRequest.status).in_(_OPEN_STATUSES))
    if _.tenant_id:
        q_open = q_open.where(RFQRequest.tenant_id == _.tenant_id)
    open_rows = (await db.exec(q_open)).all()
    unquoted = len(open_rows)
    unassigned = sum(1 for r in open_rows if not r.assigned_to)

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
    if not r or (_.tenant_id and r.tenant_id != _.tenant_id):
        raise HTTPException(status_code=404, detail="RFQ not found")

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
    if _.tenant_id and r.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")

    # Fetch linked product IDs
    product_links = (
        await db.exec(
            select(RFQProductLink).where(RFQProductLink.rfq_id == rfq_id)
        )
    ).all()

    data = _rfq_row(r, full=True)
    data["product_ids"] = [str(pl.product_id) for pl in product_links]
    return data


@tracking_router.put("/rfqs/{rfq_id}/status")
async def update_rfq_status(
    rfq_id: uuid.UUID,
    body: StatusUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if _.tenant_id and r.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
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
    db.add(r)

    await _log_rfq_event(
        db, r.id, "status_changed",
        f"Status changed from {old_status} to {body.status}",
        actor_id=_.id, tenant_id=r.tenant_id,
        detail=json.dumps({"old_status": old_status, "new_status": body.status}),
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

    return {"rfq_number": r.rfq_number, "status": r.status}


@tracking_router.put("/rfqs/{rfq_id}/assign")
async def assign_rfq(
    rfq_id: uuid.UUID,
    body: AssignUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if current_user.tenant_id and r.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    old_assigned = r.assigned_to
    r.assigned_to = body.assigned_to
    if body.priority:
        r.priority = body.priority
    r.status = "assigned"
    r.assigned_notified_at = None  # reset so notification fires again
    r.updated_at = utcnow_naive()
    db.add(r)

    summary_parts = [f"Assigned to {body.assigned_to}"]
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
        from app.services.notifications import notify_rfq_assigned
        import asyncio
        asyncio.create_task(notify_rfq_assigned(r.id))
    except Exception:
        logger.warning("rfq assign notification failed", exc_info=True)

    return {"rfq_number": r.rfq_number, "status": r.status, "assigned_to": str(r.assigned_to)}


@tracking_router.put("/rfqs/{rfq_id}/follow-up")
async def update_rfq_follow_up(
    rfq_id: uuid.UUID,
    body: FollowUpUpdate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if _.tenant_id and r.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(r, field, value)
    r.updated_at = utcnow_naive()
    db.add(r)

    for field in updates:
        event_type_map = {
            "first_response_at": "first_response",
            "quote_sent_at": "quote_sent",
            "lost_reason": "lost_reason_set",
        }
        etype = event_type_map.get(field, field)
        val = updates[field]
        await _log_rfq_event(
            db, r.id, etype,
            f"{field} recorded" if field != "lost_reason" else f"Lost reason: {val}",
            actor_id=_.id, tenant_id=r.tenant_id,
        )

    await db.commit()
    return {"rfq_number": r.rfq_number, "updated_fields": list(updates.keys())}


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
    if _.tenant_id and r.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="RFQ not found")

    rows = (
        await db.exec(
            select(RFQEvent)
            .where(RFQEvent.rfq_id == rfq_id)
            .order_by(col(RFQEvent.created_at).desc())
        )
    ).all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "summary": e.summary,
            "detail": json.loads(e.detail) if e.detail else None,
            "actor_id": str(e.actor_id) if e.actor_id else None,
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
        base["agent_run_id"] = r.agent_run_id
        base["agent_analysis_summary"] = r.agent_analysis_summary
        base["agent_draft_body"] = r.agent_draft_body
    return base
