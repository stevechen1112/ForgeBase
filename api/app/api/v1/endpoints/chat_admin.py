"""
Chat Admin API — review chat sessions and messages (admin only)

GET   /chat/admin/sessions              — list all chat sessions
GET   /chat/admin/sessions/{id}         — session detail with all messages
PATCH /chat/admin/sessions/{id}         — update quality_rating / admin_notes
"""
import json as _json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_admin
from app.db.session import get_session
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.models.visitor import Visitor

router = APIRouter(prefix="/chat/admin", tags=["Chat Admin"])


# ── Schemas ───────────────────────────────────────────────────────────────────


class ChatSessionUpdate(BaseModel):
    quality_rating: Optional[int] = None
    admin_notes: Optional[str] = None

    @field_validator("quality_rating")
    @classmethod
    def validate_rating(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 5):
            raise ValueError("quality_rating must be between 1 and 5")
        return v


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/sessions")
async def list_chat_sessions(
    status_filter: Optional[str] = Query(None, alias="status"),
    quality_rating: Optional[int] = None,
    has_notes: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """List all chat sessions with optional filters. Sorted by most recent first."""
    q = select(ChatSession).order_by(col(ChatSession.started_at).desc())

    if current_user.tenant_id:
        q = q.where(ChatSession.tenant_id == current_user.tenant_id)
    if status_filter:
        q = q.where(ChatSession.status == status_filter)
    if quality_rating is not None:
        q = q.where(ChatSession.quality_rating == quality_rating)
    if has_notes is True:
        q = q.where(ChatSession.admin_notes.isnot(None))  # type: ignore[union-attr]
    elif has_notes is False:
        q = q.where(ChatSession.admin_notes.is_(None))  # type: ignore[union-attr]

    # Get total count for pagination
    count_q = select(func.count()).select_from(ChatSession)
    if current_user.tenant_id:
        count_q = count_q.where(ChatSession.tenant_id == current_user.tenant_id)
    if status_filter:
        count_q = count_q.where(ChatSession.status == status_filter)
    if quality_rating is not None:
        count_q = count_q.where(ChatSession.quality_rating == quality_rating)
    if has_notes is True:
        count_q = count_q.where(ChatSession.admin_notes.isnot(None))  # type: ignore[union-attr]
    elif has_notes is False:
        count_q = count_q.where(ChatSession.admin_notes.is_(None))  # type: ignore[union-attr]
    total = (await db.exec(count_q)).one()

    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()

    # Batch-fetch visitor info for display
    visitor_ids = list({r.visitor_id for r in rows})
    visitors_map: dict[uuid.UUID, Visitor] = {}
    if visitor_ids:
        v_rows = (await db.exec(
            select(Visitor).where(Visitor.visitor_id.in_(visitor_ids))  # type: ignore[union-attr]
        )).all()
        visitors_map = {v.visitor_id: v for v in v_rows}

    items = []
    for s in rows:
        v = visitors_map.get(s.visitor_id)
        items.append({
            "id": str(s.id),
            "visitor_id": str(s.visitor_id),
            "visitor_intent_stage": v.intent_stage if v else None,
            "visitor_intent_score": v.intent_score if v else None,
            "visitor_country": v.country if v else None,
            "context_page": s.context_page,
            "context_entity_type": s.context_entity_type,
            "status": s.status,
            "message_count": s.message_count,
            "quality_rating": s.quality_rating,
            "admin_notes": s.admin_notes,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/sessions/{chat_session_id}")
async def get_chat_session_detail(
    chat_session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Get a single chat session with all messages."""
    session = await db.get(ChatSession, chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if current_user.tenant_id and session.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Fetch all messages in chronological order
    msgs = (await db.exec(
        select(ChatMessage)
        .where(ChatMessage.chat_session_id == chat_session_id)
        .order_by(col(ChatMessage.created_at).asc())
    )).all()

    # Fetch visitor info
    visitor = await db.get(Visitor, session.visitor_id)

    return {
        "id": str(session.id),
        "visitor_id": str(session.visitor_id),
        "visitor_intent_stage": visitor.intent_stage if visitor else None,
        "visitor_intent_score": visitor.intent_score if visitor else None,
        "visitor_country": visitor.country if visitor else None,
        "visitor_device_type": visitor.device_type if visitor else None,
        "context_page": session.context_page,
        "context_entity_type": session.context_entity_type,
        "context_entity_id": str(session.context_entity_id) if session.context_entity_id else None,
        "status": session.status,
        "message_count": session.message_count,
        "quality_rating": session.quality_rating,
        "admin_notes": session.admin_notes,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "sources": _json.loads(m.sources) if m.sources else [],
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }


@router.patch("/sessions/{chat_session_id}")
async def update_chat_session(
    chat_session_id: uuid.UUID,
    body: ChatSessionUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
):
    """Update quality_rating or admin_notes on a chat session."""
    session = await db.get(ChatSession, chat_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    if current_user.tenant_id and session.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if "quality_rating" in body.model_fields_set:
        session.quality_rating = body.quality_rating
    if "admin_notes" in body.model_fields_set:
        session.admin_notes = body.admin_notes

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "id": str(session.id),
        "quality_rating": session.quality_rating,
        "admin_notes": session.admin_notes,
    }
