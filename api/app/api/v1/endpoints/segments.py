"""
Audience Segment API  (2.1.1)

Multi-condition visitor segment definitions.
Conditions supported:
  - intent_stage:  {"type":"intent_stage","op":"eq","value":"hot"}
  - intent_score:  {"type":"intent_score","op":"gte","value":60}
  - country:       {"type":"country","op":"eq","value":"US"}
  - tag:           {"type":"tag","tag_id":"<uuid>"}
  - event_count:   {"type":"event_count","event_name":"product_view","op":"gte","value":3,"within_days":30}

GET    /tracking/segments              — list segments (admin)
POST   /tracking/segments              — create segment (admin)
GET    /tracking/segments/{id}         — get segment (admin)
PATCH  /tracking/segments/{id}         — update segment (admin)
DELETE /tracking/segments/{id}         — delete segment (admin)
POST   /tracking/segments/{id}/evaluate — evaluate segment → matching visitor count + sample
"""
import json
import uuid
from datetime import datetime, timedelta
from app.core.datetime import utcnow_naive
from typing import Optional
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select, col, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user, require_admin
from app.db.session import get_session
from app.models.segment import Segment
from app.models.visitor import Visitor
from app.models.tracking_event import TrackingEvent
from app.models.audience_tag import VisitorTagLink
from app.models.contact import Contact
from app.models.user import User

router = APIRouter(prefix="/tracking", tags=["Audience Segments"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ConditionItem(BaseModel):
    type: str
    op: Optional[str] = None
    value: Optional[str | int | float] = None
    event_name: Optional[str] = None
    within_days: Optional[int] = None
    tag_id: Optional[str] = None


class SegmentCreate(BaseModel):
    name: str
    description: str = ""
    conditions: list[ConditionItem]
    combinator: str = "AND"


class SegmentRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    conditions: list[dict]
    combinator: str
    created_by: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    member_count: Optional[int] = None

    model_config = {"from_attributes": True}


class SegmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[list[ConditionItem]] = None
    combinator: Optional[str] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

def _segment_filters(
    conditions: list[dict],
    combinator: str,
    tenant_id: Optional[uuid.UUID],
):
    """Build SQLAlchemy filter for visitor segment conditions."""
    filters = []
    for cond in conditions:
        ctype = cond.get("type")
        op = cond.get("op", "eq")
        value = cond.get("value")

        if ctype == "intent_stage" and value:
            if op == "eq":
                filters.append(Visitor.intent_stage == value)

        elif ctype == "intent_score" and value is not None:
            if op == "gte":
                filters.append(Visitor.intent_score >= int(value))
            elif op == "lte":
                filters.append(Visitor.intent_score <= int(value))
            elif op == "eq":
                filters.append(Visitor.intent_score == int(value))

        elif ctype == "country" and value:
            if op == "eq":
                filters.append(Visitor.country == value)

        elif ctype == "tag":
            tag_id = cond.get("tag_id")
            if tag_id:
                tag_subq = select(VisitorTagLink.visitor_id).where(
                    VisitorTagLink.tag_id == uuid.UUID(tag_id)
                )
                filters.append(Visitor.visitor_id.in_(tag_subq))

        elif ctype == "event_count":
            event_name = cond.get("event_name")
            within_days = cond.get("within_days", 30)
            if event_name and value is not None:
                since = utcnow_naive() - timedelta(days=int(within_days))
                event_subq = (
                    select(TrackingEvent.visitor_id)
                    .where(
                        TrackingEvent.event_name == event_name,
                        TrackingEvent.timestamp >= since,
                        TrackingEvent.visitor_id.is_not(None),
                    )
                    .group_by(TrackingEvent.visitor_id)
                    .having(func.count(TrackingEvent.event_id) >= int(value))
                )
                if tenant_id:
                    event_subq = event_subq.where(TrackingEvent.tenant_id == tenant_id)
                if op == "gte":
                    filters.append(Visitor.visitor_id.in_(event_subq))

    if not filters:
        return None
    from sqlalchemy import and_, or_
    return and_(*filters) if combinator == "AND" else or_(*filters)


async def _count_segment_matches(
    db: AsyncSession,
    conditions: list[dict],
    combinator: str,
    tenant_id: Optional[uuid.UUID],
) -> int:
    q = select(Visitor.visitor_id)
    if tenant_id:
        q = q.where(Visitor.tenant_id == tenant_id)
    combined = _segment_filters(conditions, combinator, tenant_id)
    if combined is not None:
        q = q.where(combined)
    count_q = select(func.count()).select_from(q.subquery())
    return (await db.exec(count_q)).one()


def _to_segment_read(s: Segment, member_count: Optional[int] = None) -> SegmentRead:
    return SegmentRead(
        id=s.id,
        name=s.name,
        description=s.description,
        conditions=json.loads(s.conditions),
        combinator=s.combinator,
        created_by=s.created_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
        member_count=member_count,
    )


@router.get("/segments", response_model=list[SegmentRead])
async def list_segments(
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rows = (await db.exec(select(Segment).order_by(Segment.created_at.desc()))).all()
    result: list[SegmentRead] = []
    for s in rows:
        conditions = json.loads(s.conditions)
        member_count = await _count_segment_matches(
            db, conditions, s.combinator, _.tenant_id
        )
        result.append(_to_segment_read(s, member_count=member_count))
    return result


@router.post("/segments", response_model=SegmentRead, status_code=status.HTTP_201_CREATED)
async def create_segment(
    payload: SegmentCreate,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if payload.combinator not in ("AND", "OR"):
        raise HTTPException(status_code=422, detail="combinator must be AND or OR")
    seg = Segment(
        name=payload.name,
        description=payload.description,
        conditions=json.dumps([c.model_dump(exclude_none=True) for c in payload.conditions]),
        combinator=payload.combinator,
        created_by=current_user.id,
    )
    db.add(seg)
    await db.commit()
    await db.refresh(seg)
    return _to_segment_read(seg)


@router.get("/segments/{segment_id}", response_model=SegmentRead)
async def get_segment(
    segment_id: uuid.UUID,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    seg = await db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    member_count = await _count_segment_matches(
        db, json.loads(seg.conditions), seg.combinator, _.tenant_id
    )
    return _to_segment_read(seg, member_count=member_count)


@router.patch("/segments/{segment_id}", response_model=SegmentRead)
async def update_segment(
    segment_id: uuid.UUID,
    payload: SegmentUpdate,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    seg = await db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    if payload.name is not None:
        seg.name = payload.name
    if payload.description is not None:
        seg.description = payload.description
    if payload.conditions is not None:
        seg.conditions = json.dumps([c.model_dump(exclude_none=True) for c in payload.conditions])
    if payload.combinator is not None:
        if payload.combinator not in ("AND", "OR"):
            raise HTTPException(status_code=422, detail="combinator must be AND or OR")
        seg.combinator = payload.combinator
    seg.updated_at = utcnow_naive()
    db.add(seg)
    await db.commit()
    await db.refresh(seg)
    member_count = await _count_segment_matches(
        db, json.loads(seg.conditions), seg.combinator, _.tenant_id
    )
    return _to_segment_read(seg, member_count=member_count)


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    segment_id: uuid.UUID,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    seg = await db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    await db.delete(seg)
    await db.commit()


# ── Evaluate ──────────────────────────────────────────────────────────────────

@router.post("/segments/{segment_id}/evaluate")
async def evaluate_segment(
    segment_id: uuid.UUID,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Evaluate the segment definition against the current visitor table.
    Returns: total matching count + up to 20 sample visitor_ids.
    """
    seg = await db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    conditions: list[dict] = json.loads(seg.conditions)
    combinator = seg.combinator  # "AND" | "OR"

    q = select(Visitor.visitor_id)
    if _.tenant_id:
        q = q.where(Visitor.tenant_id == _.tenant_id)
    combined = _segment_filters(conditions, combinator, _.tenant_id)
    if combined is not None:
        q = q.where(combined)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.exec(count_q)).one()
    sample_rows = (await db.exec(q.limit(20))).all()

    return {
        "segment_id": str(segment_id),
        "total_matches": total,
        "sample_visitor_ids": [str(r) for r in sample_rows],
    }


# ── Sync to ESP ───────────────────────────────────────────────────────────────

@router.post("/segments/{segment_id}/sync-to-esp")
async def sync_segment_to_esp(
    segment_id: uuid.UUID,
    provider: str,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Evaluate the segment and sync matching contacts to the selected ESP.

    Matching logic mirrors evaluate_segment; contacts are resolved via
    Contact.visitor_id (tenant-scoped). Currently supports SendGrid and
    Mailchimp. Returns counts for transparency.
    """
    if provider not in ("sendgrid", "mailchimp"):
        raise HTTPException(status_code=422, detail="provider must be 'sendgrid' or 'mailchimp'")

    from app.core.config import settings
    from app.services.esp_service import sendgrid_upsert_contact, mailchimp_upsert_member

    seg = await db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")

    if provider == "sendgrid" and not settings.SENDGRID_API_KEY:
        raise HTTPException(status_code=400, detail="SendGrid not configured: set SENDGRID_API_KEY.")
    if provider == "mailchimp" and not (settings.MAILCHIMP_API_KEY and settings.MAILCHIMP_AUDIENCE_ID):
        raise HTTPException(status_code=400, detail="Mailchimp not configured: set MAILCHIMP_API_KEY and MAILCHIMP_AUDIENCE_ID.")

    # Re-run the same evaluation to get the full set of matching visitor_ids
    conditions: list[dict] = json.loads(seg.conditions)
    combinator = seg.combinator

    q = select(Visitor.visitor_id)
    if _.tenant_id:
        q = q.where(Visitor.tenant_id == _.tenant_id)
    filters = []

    for cond in conditions:
        ctype = cond.get("type")
        op = cond.get("op", "eq")
        value = cond.get("value")

        if ctype == "intent_stage" and value:
            if op == "eq":
                filters.append(Visitor.intent_stage == value)
        elif ctype == "intent_score" and value is not None:
            if op == "gte":
                filters.append(Visitor.intent_score >= int(value))
            elif op == "lte":
                filters.append(Visitor.intent_score <= int(value))
            elif op == "eq":
                filters.append(Visitor.intent_score == int(value))
        elif ctype == "country" and value:
            if op == "eq":
                filters.append(Visitor.country == value)
        elif ctype == "tag":
            tag_id = cond.get("tag_id")
            if tag_id:
                tag_subq = select(VisitorTagLink.visitor_id).where(
                    VisitorTagLink.tag_id == uuid.UUID(tag_id)
                )
                filters.append(Visitor.visitor_id.in_(tag_subq))
        elif ctype == "event_count":
            event_name = cond.get("event_name")
            within_days = cond.get("within_days", 30)
            if event_name and value is not None:
                since = utcnow_naive() - timedelta(days=int(within_days))
                event_subq = (
                    select(TrackingEvent.visitor_id)
                    .where(
                        TrackingEvent.event_name == event_name,
                        TrackingEvent.timestamp >= since,
                        TrackingEvent.visitor_id.is_not(None),
                    )
                    .group_by(TrackingEvent.visitor_id)
                    .having(func.count(TrackingEvent.event_id) >= int(value))
                )
                if _.tenant_id:
                    event_subq = event_subq.where(TrackingEvent.tenant_id == _.tenant_id)
                if op == "gte":
                    filters.append(Visitor.visitor_id.in_(event_subq))

    if filters:
        from sqlalchemy import and_, or_
        combined = and_(*filters) if combinator == "AND" else or_(*filters)
        q = q.where(combined)

    matching_visitor_ids = (await db.exec(q)).all()

    # Resolve to contacts (tenant-scoped)
    contact_q = select(Contact).where(Contact.visitor_id.in_(matching_visitor_ids))
    if _.tenant_id:
        contact_q = contact_q.where(Contact.tenant_id == _.tenant_id)
    contacts = (await db.exec(contact_q)).all()

    success = 0
    failed = 0
    for contact in contacts:
        full_name: str = contact.full_name or ""
        parts = full_name.split(" ", 1)

        if provider == "sendgrid":
            result = await sendgrid_upsert_contact(
                email=contact.email,
                first_name=parts[0] if parts else "",
                last_name=parts[1] if len(parts) > 1 else "",
            )
        else:
            tags = []
            if contact.lifecycle_stage:
                tags.append(contact.lifecycle_stage)
            if contact.company_name:
                tags.append(f"company:{contact.company_name}")
            result = await mailchimp_upsert_member(
                email=contact.email,
                first_name=parts[0] if parts else "",
                last_name=parts[1] if len(parts) > 1 else "",
                tags=tags,
            )

        if "error" in result or result.get("skipped"):
            failed += 1
        else:
            success += 1

        await asyncio.sleep(0.05)

    return {
        "segment_id": str(segment_id),
        "provider": provider,
        "visitors_matched": len(matching_visitor_ids),
        "contacts_matched": len(contacts),
        "total": len(contacts),
        "success": success,
        "failed": failed,
    }
