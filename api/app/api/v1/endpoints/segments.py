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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select, col, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_super_admin
from app.db.session import get_session
from app.models.segment import Segment
from app.models.visitor import Visitor
from app.models.tracking_event import TrackingEvent
from app.models.audience_tag import VisitorTagLink
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

    model_config = {"from_attributes": True}


class SegmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[list[ConditionItem]] = None
    combinator: Optional[str] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/segments", response_model=list[SegmentRead])
async def list_segments(
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rows = (await db.exec(select(Segment).order_by(Segment.created_at.desc()))).all()
    return [
        SegmentRead(
            id=s.id,
            name=s.name,
            description=s.description,
            conditions=json.loads(s.conditions),
            combinator=s.combinator,
            created_by=s.created_by,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in rows
    ]


@router.post("/segments", response_model=SegmentRead, status_code=status.HTTP_201_CREATED)
async def create_segment(
    payload: SegmentCreate,
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
    return SegmentRead(
        id=seg.id,
        name=seg.name,
        description=seg.description,
        conditions=json.loads(seg.conditions),
        combinator=seg.combinator,
        created_by=seg.created_by,
        created_at=seg.created_at,
        updated_at=seg.updated_at,
    )


@router.get("/segments/{segment_id}", response_model=SegmentRead)
async def get_segment(
    segment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    seg = await db.get(Segment, segment_id)
    if not seg:
        raise HTTPException(status_code=404, detail="Segment not found")
    return SegmentRead(
        id=seg.id,
        name=seg.name,
        description=seg.description,
        conditions=json.loads(seg.conditions),
        combinator=seg.combinator,
        created_by=seg.created_by,
        created_at=seg.created_at,
        updated_at=seg.updated_at,
    )


@router.patch("/segments/{segment_id}", response_model=SegmentRead)
async def update_segment(
    segment_id: uuid.UUID,
    payload: SegmentUpdate,
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
    return SegmentRead(
        id=seg.id,
        name=seg.name,
        description=seg.description,
        conditions=json.loads(seg.conditions),
        combinator=seg.combinator,
        created_by=seg.created_by,
        created_at=seg.created_at,
        updated_at=seg.updated_at,
    )


@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    segment_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_super_admin),
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

    # Start with all visitors
    q = select(Visitor.visitor_id)
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
                # Subquery: visitors with event_count >= value
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
                if op == "gte":
                    filters.append(Visitor.visitor_id.in_(event_subq))

    # Apply combinator
    if filters:
        from sqlalchemy import and_, or_
        combined = and_(*filters) if combinator == "AND" else or_(*filters)
        q = q.where(combined)

    # Count + sample
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.exec(count_q)).one()
    sample_rows = (await db.exec(q.limit(20))).all()

    return {
        "segment_id": str(segment_id),
        "total_matches": total,
        "sample_visitor_ids": [str(r) for r in sample_rows],
    }
