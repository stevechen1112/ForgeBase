"""
ContentStrategy CRUD + PageBrief lifecycle transitions.
"""
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.session import get_session
from app.api.v1.deps import require_content_editor, require_admin
from app.models.content_strategy import ContentStrategy
from app.models.page_brief import PageBrief
from app.schemas.content import (
    ContentStrategyCreate,
    ContentStrategyUpdate,
    ContentStrategyRead,
    BriefStatusTransition,
    PageBriefRead,
)

router = APIRouter()

# ── Valid state transitions for brief_status ──────────────────────────────────
BRIEF_TRANSITIONS: dict[str, dict[str, str]] = {
    "approve":           {"from": "draft",       "to": "approved"},
    "start":             {"from": "approved",     "to": "in_progress"},
    "complete":          {"from": "in_progress",  "to": "completed"},
    "publish":           {"from": "completed",    "to": "published"},
    "request_revision":  {"from": "completed",    "to": "revision"},
}


# ── ContentStrategy endpoints ─────────────────────────────────────────────────

@router.get("/strategies", tags=["content_strategy"])
async def list_strategies(
    page_type: Optional[str] = Query(default=None),
    locale: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _=Depends(require_content_editor),
):
    q = select(ContentStrategy)
    if page_type:
        q = q.where(ContentStrategy.page_type == page_type)
    if locale:
        q = q.where(ContentStrategy.locale == locale)
    if status:
        q = q.where(ContentStrategy.status == status)

    total_result = await session.execute(q)
    total = len(total_result.scalars().all())

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    items = result.scalars().all()

    return {
        "data": [ContentStrategyRead.model_validate(i) for i in items],
        "meta": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, -(-total // page_size)),
        },
    }


@router.post("/strategies", tags=["content_strategy"], status_code=201)
async def create_strategy(
    payload: ContentStrategyCreate,
    session: AsyncSession = Depends(get_session),
    _=Depends(require_content_editor),
):
    item = ContentStrategy(**payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"data": ContentStrategyRead.model_validate(item)}


@router.get("/strategies/{strategy_id}", tags=["content_strategy"])
async def get_strategy(
    strategy_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _=Depends(require_content_editor),
):
    item = await session.get(ContentStrategy, strategy_id)
    if not item:
        raise HTTPException(status_code=404, detail="ContentStrategy not found")
    return {"data": ContentStrategyRead.model_validate(item)}


@router.patch("/strategies/{strategy_id}", tags=["content_strategy"])
async def update_strategy(
    strategy_id: uuid.UUID,
    payload: ContentStrategyUpdate,
    session: AsyncSession = Depends(get_session),
    _=Depends(require_content_editor),
):
    item = await session.get(ContentStrategy, strategy_id)
    if not item:
        raise HTTPException(status_code=404, detail="ContentStrategy not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    item.updated_at = utcnow_naive()
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return {"data": ContentStrategyRead.model_validate(item)}


@router.delete("/strategies/{strategy_id}", status_code=204, tags=["content_strategy"])
async def delete_strategy(
    strategy_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _=Depends(require_admin),
):
    item = await session.get(ContentStrategy, strategy_id)
    if not item:
        raise HTTPException(status_code=404, detail="ContentStrategy not found")
    await session.delete(item)
    await session.commit()


# ── PageBrief lifecycle transitions ───────────────────────────────────────────

@router.post("/briefs/{brief_id}/transition", tags=["page_briefs"])
async def transition_brief(
    brief_id: uuid.UUID,
    payload: BriefStatusTransition,
    session: AsyncSession = Depends(get_session),
    _=Depends(require_content_editor),
):
    """Advance or revert a PageBrief through its lifecycle state machine."""
    brief = await session.get(PageBrief, brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="PageBrief not found")

    transition = BRIEF_TRANSITIONS.get(payload.action)
    if not transition:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action '{payload.action}'. Valid actions: {list(BRIEF_TRANSITIONS.keys())}",
        )

    if brief.brief_status != transition["from"]:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot '{payload.action}': brief is in '{brief.brief_status}', expected '{transition['from']}'",
        )

    brief.brief_status = transition["to"]
    brief.updated_at = utcnow_naive()
    session.add(brief)
    await session.commit()
    await session.refresh(brief)
    return {"data": PageBriefRead.model_validate(brief)}
