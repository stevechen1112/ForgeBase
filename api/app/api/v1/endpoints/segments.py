"""
Audience Segment API  (2.1.1)

Multi-condition visitor segment definitions.
Conditions supported:
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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from pydantic import Field as PydanticField
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import (
    RequireFeature,
    get_current_user,
    require_admin,
    require_user_tenant_id,
)
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.audience_tag import VisitorTagLink
from app.models.segment import Segment
from app.models.tracking_event import TrackingEvent
from app.models.user import User
from app.models.visitor import Visitor

router = APIRouter(prefix="/tracking", tags=["Audience Segments"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ConditionItem(BaseModel):
    type: str = PydanticField(max_length=30)
    op: Optional[str] = None
    value: Optional[str | int | float] = None
    event_name: Optional[str] = PydanticField(default=None, max_length=50)
    within_days: Optional[int] = PydanticField(default=None, ge=1, le=365)
    tag_id: Optional[uuid.UUID] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in {"country", "tag", "event_count"}:
            raise ValueError("Unsupported segment condition type")
        return value

    @field_validator("op")
    @classmethod
    def validate_op(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in {"eq", "gte", "lte", "in"}:
            raise ValueError("Unsupported segment condition operator")
        return value


class SegmentCreate(BaseModel):
    name: str = PydanticField(min_length=1, max_length=100)
    description: str = PydanticField(default="", max_length=300)
    conditions: list[ConditionItem] = PydanticField(max_length=20)
    combinator: str = "AND"


class SegmentPreviewRequest(BaseModel):
    """Read-only conditions preview; it never creates a temporary segment."""

    conditions: list[ConditionItem] = PydanticField(min_length=1, max_length=20)
    combinator: str = "AND"


class SegmentRead(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
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
    name: Optional[str] = PydanticField(default=None, min_length=1, max_length=100)
    description: Optional[str] = PydanticField(default=None, max_length=300)
    conditions: Optional[list[ConditionItem]] = PydanticField(default=None, max_length=20)
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

        if ctype == "country" and value:
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
        tenant_id=s.tenant_id,
        name=s.name,
        description=s.description,
        conditions=json.loads(s.conditions),
        combinator=s.combinator,
        created_by=s.created_by,
        created_at=s.created_at,
        updated_at=s.updated_at,
        member_count=member_count,
    )


async def _get_owned_segment(
    db: AsyncSession, segment_id: uuid.UUID, current_user: User
) -> Segment:
    tenant_id = require_user_tenant_id(current_user)
    segment = (
        await db.exec(
            select(Segment).where(
                Segment.id == segment_id,
                Segment.tenant_id == tenant_id,
            )
        )
    ).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.get("/segments", response_model=list[SegmentRead])
async def list_segments(
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    tenant_id = require_user_tenant_id(_)
    rows = (
        await db.exec(
            select(Segment)
            .where(Segment.tenant_id == tenant_id)
            .order_by(Segment.created_at.desc())
        )
    ).all()
    result: list[SegmentRead] = []
    for s in rows:
        conditions = json.loads(s.conditions)
        member_count = await _count_segment_matches(
            db, conditions, s.combinator, tenant_id
        )
        result.append(_to_segment_read(s, member_count=member_count))
    return result


@router.post("/segments", response_model=SegmentRead, status_code=status.HTTP_201_CREATED)
async def create_segment(
    payload: SegmentCreate,
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if payload.combinator not in ("AND", "OR"):
        raise HTTPException(status_code=422, detail="combinator must be AND or OR")
    seg = Segment(
        tenant_id=require_user_tenant_id(current_user),
        name=payload.name,
        description=payload.description,
        conditions=json.dumps([c.model_dump(mode="json", exclude_none=True) for c in payload.conditions]),
        combinator=payload.combinator,
        created_by=current_user.id,
    )
    db.add(seg)
    await db.commit()
    await db.refresh(seg)
    return _to_segment_read(seg)


@router.post("/segments/preview")
async def preview_segment(
    payload: SegmentPreviewRequest,
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return a matching count for unsaved conditions without changing tenant data."""
    if payload.combinator not in ("AND", "OR"):
        raise HTTPException(status_code=422, detail="combinator must be AND or OR")
    tenant_id = require_user_tenant_id(current_user)
    conditions = [item.model_dump(mode="json", exclude_none=True) for item in payload.conditions]
    total = await _count_segment_matches(db, conditions, payload.combinator, tenant_id)
    return {"total_matches": total}


@router.get("/segments/{segment_id}", response_model=SegmentRead)
async def get_segment(
    segment_id: uuid.UUID,
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    seg = await _get_owned_segment(db, segment_id, _)
    member_count = await _count_segment_matches(
        db, json.loads(seg.conditions), seg.combinator, _.tenant_id
    )
    return _to_segment_read(seg, member_count=member_count)


@router.patch("/segments/{segment_id}", response_model=SegmentRead)
async def update_segment(
    segment_id: uuid.UUID,
    payload: SegmentUpdate,
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    seg = await _get_owned_segment(db, segment_id, _)
    if payload.name is not None:
        seg.name = payload.name
    if payload.description is not None:
        seg.description = payload.description
    if payload.conditions is not None:
        seg.conditions = json.dumps([c.model_dump(mode="json", exclude_none=True) for c in payload.conditions])
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
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_admin),
):
    seg = await _get_owned_segment(db, segment_id, _)
    await db.delete(seg)
    await db.commit()


# ── Evaluate ──────────────────────────────────────────────────────────────────

@router.post("/segments/{segment_id}/evaluate")
async def evaluate_segment(
    segment_id: uuid.UUID,
    _feature: User = Depends(RequireFeature("audience_segments")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Evaluate the segment definition against the current visitor table.
    Returns: total matching count + up to 20 sample visitor_ids.
    """
    seg = await _get_owned_segment(db, segment_id, _)

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
