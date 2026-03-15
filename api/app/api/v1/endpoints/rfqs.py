"""
RFQ API — 1b.4.4, 1b.4.5, 1b.4.6, 1b.4.8

POST /forms/rfq              — submit RFQ form (public, no auth)
GET  /tracking/rfqs          — list RFQs with filters (admin)
GET  /tracking/rfqs/{id}     — RFQ detail (admin)
PUT  /tracking/rfqs/{id}/status   — update status  (admin)
PUT  /tracking/rfqs/{id}/assign   — assign to sales user (admin)
"""
import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlmodel import select, col, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.contact import Contact
from app.models.rfq_request import RFQRequest, RFQProductLink
from app.models.visitor import Visitor
from app.models.user import User

# Two routers — public forms_router + admin tracking_router
forms_router = APIRouter(prefix="/forms", tags=["Forms"])
tracking_router = APIRouter(prefix="/tracking", tags=["Tracking"])

VALID_STATUSES = {"new", "assigned", "in_progress", "quoted", "won", "lost", "expired"}
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


@forms_router.post("/rfq", status_code=status.HTTP_201_CREATED)
async def submit_rfq(
    body: RFQFormIn,
    db: AsyncSession = Depends(get_session),
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

    # ── 2. Upsert Contact ────────────────────────────────────────────────
    now = utcnow_naive()
    contact = (
        await db.exec(select(Contact).where(Contact.email == body.email))
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

    await db.commit()

    # ── 7. Trigger routing + notification + HubSpot + webhook (async, non-blocking)
    # Imported inline to avoid circular dependency at module load time
    try:
        from app.services.rfq_routing import route_rfq
        from app.services.notifications import notify_new_rfq
        from app.services.hubspot import sync_rfq_to_hubspot
        from app.services.webhook import fire_webhook
        import asyncio
        asyncio.create_task(route_rfq(rfq.id))
        asyncio.create_task(notify_new_rfq(rfq.id))
        asyncio.create_task(sync_rfq_to_hubspot(rfq.id))
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
        pass  # routing failures must not block form submission

    return {
        "rfq_number": rfq_number,
        "rfq_id": str(rfq.id),
        "priority": priority,
    }


# ── Admin: RFQ management ─────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str

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
    lost_reason: Optional[str] = None


@tracking_router.get("/rfqs")
async def list_rfqs(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[uuid.UUID] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    q = select(RFQRequest).order_by(col(RFQRequest.created_at).desc())
    if status:
        q = q.where(RFQRequest.status == status)
    if priority:
        q = q.where(RFQRequest.priority == priority)
    if assigned_to:
        q = q.where(RFQRequest.assigned_to == assigned_to)
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    return [_rfq_row(r) for r in rows]


@tracking_router.get("/rfqs/{rfq_id}")
async def get_rfq(
    rfq_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    r = await db.get(RFQRequest, rfq_id)
    if not r:
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
    old_status = r.status
    r.status = body.status
    r.updated_at = utcnow_naive()
    if body.status in ("won", "lost", "expired"):
        r.closed_at = r.updated_at
    db.add(r)
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
        pass

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
    r.assigned_to = body.assigned_to
    if body.priority:
        r.priority = body.priority
    r.status = "assigned"
    r.assigned_notified_at = None  # reset so notification fires again
    r.updated_at = utcnow_naive()
    db.add(r)
    await db.commit()

    # Trigger assignment notification
    try:
        from app.services.notifications import notify_rfq_assigned
        import asyncio
        asyncio.create_task(notify_rfq_assigned(r.id))
    except Exception:
        pass

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
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(r, field, value)
    r.updated_at = utcnow_naive()
    db.add(r)
    await db.commit()
    return {"rfq_number": r.rfq_number, "updated_fields": list(updates.keys())}


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
        "assigned_to": str(r.assigned_to) if r.assigned_to else None,
        "created_at": r.created_at.isoformat(),
    }
    if full:
        base["application_id"] = str(r.application_id) if r.application_id else None
        base["source_page"] = r.source_page
        base["hubspot_deal_id"] = r.hubspot_deal_id
        base["form_data"] = json.loads(r.form_data) if r.form_data else None
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
    return base
