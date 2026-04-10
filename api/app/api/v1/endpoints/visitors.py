"""
Visitor & Session Management API  (1b.2.1, 1b.2.2, 1b.2.5)

GET  /tracking/visitors               — list visitors (admin)
GET  /tracking/visitors/{id}          — visitor detail + event timeline
GET  /tracking/visitors/{id}/events   — visitor events timeline
GET  /tracking/visitors/{id}/journey  — unified journey timeline
GET  /tracking/sessions/{id}          — session detail
GET  /tracking/audiences              — list audience tags (admin)
POST /tracking/audiences              — create audience tag (admin)
POST /tracking/visitors/{id}/tags     — assign tag to visitor (admin)
DELETE /tracking/visitors/{id}/tags/{tag_id} — remove tag from visitor (admin)
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select, col, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.visitor import Visitor
from app.models.audience_tag import AudienceTag, VisitorTagLink
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.models.rfq_request import RFQRequest

router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ── Visitor endpoints ─────────────────────────────────────────────────────────

@router.get("/visitors")
async def list_visitors(
    intent_stage: Optional[str] = None,
    min_score: Optional[int] = None,
    country: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """List visitors sorted by intent score (desc). Admin only."""
    q = select(Visitor).order_by(col(Visitor.intent_score).desc())
    if _.tenant_id:
        q = q.where(Visitor.tenant_id == _.tenant_id)
    if intent_stage:
        q = q.where(Visitor.intent_stage == intent_stage)
    if min_score is not None:
        q = q.where(Visitor.intent_score >= min_score)
    if country:
        q = q.where(Visitor.country == country)
    q = q.offset(offset).limit(min(limit, 200))
    rows = (await db.exec(q)).all()
    return [
        {
            "visitor_id": str(r.visitor_id),
            "intent_score": r.intent_score,
            "intent_stage": r.intent_stage,
            "total_visits": r.total_visits,
            "total_page_views": r.total_page_views,
            "device_type": r.device_type,
            "country": r.country,
            "contact_id": str(r.contact_id) if r.contact_id else None,
            "last_seen": r.last_seen.isoformat(),
            "first_seen": r.first_seen.isoformat(),
        }
        for r in rows
    ]


@router.get("/visitors/{visitor_id}")
async def get_visitor(
    visitor_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    v = await db.get(Visitor, visitor_id)
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if _.tenant_id and v.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="Visitor not found")

    # Count event breakdown
    counts = (await db.exec(
        select(TrackingEvent.event_name, func.count(TrackingEvent.event_id).label("c"))
        .where(TrackingEvent.visitor_id == visitor_id)
        .group_by(TrackingEvent.event_name)
    )).all()

    return {
        "visitor_id": str(v.visitor_id),
        "intent_score": v.intent_score,
        "intent_stage": v.intent_stage,
        "total_visits": v.total_visits,
        "total_page_views": v.total_page_views,
        "device_type": v.device_type,
        "country": v.country,
        "contact_id": str(v.contact_id) if v.contact_id else None,
        "last_seen": v.last_seen.isoformat(),
        "first_seen": v.first_seen.isoformat(),
        "event_breakdown": {row[0]: row[1] for row in counts},
    }


@router.get("/visitors/{visitor_id}/events")
async def visitor_event_timeline(
    visitor_id: uuid.UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Return chronological event timeline for a visitor."""
    import json as _json
    rows = (await db.exec(
        select(TrackingEvent)
        .where(TrackingEvent.visitor_id == visitor_id)
        .order_by(col(TrackingEvent.timestamp).desc())
        .limit(min(limit, 500))
    )).all()
    return [
        {
            "event_id": str(r.event_id),
            "event_name": r.event_name,
            "timestamp": r.timestamp.isoformat(),
            "page_url": r.page_url,
            "page_type": r.page_type,
            "score_delta": r.score_delta,
            "properties": _json.loads(r.properties) if r.properties else None,
        }
        for r in rows
    ]


# ── Session endpoints ─────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    ts = await db.get(TrackingSession, session_id)
    if not ts:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": str(ts.session_id),
        "visitor_id": str(ts.visitor_id),
        "start_time": ts.start_time.isoformat(),
        "end_time": ts.end_time.isoformat() if ts.end_time else None,
        "page_count": ts.page_count,
        "entry_page": ts.entry_page,
        "exit_page": ts.exit_page,
        "traffic_source": ts.traffic_source,
        "referrer": ts.referrer,
        "utm_source": ts.utm_source,
        "utm_medium": ts.utm_medium,
        "utm_campaign": ts.utm_campaign,
        "device_type": ts.device_type,
        "country": ts.country,
    }


# ── Visitor Journey (P2: unified timeline) ────────────────────────────────────

@router.get("/visitors/{visitor_id}/journey")
async def visitor_journey(
    visitor_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Unified journey timeline for a single visitor.
    Combines: visitor profile, tracking events, chat sessions, RFQs.
    """
    import json as _json

    v = await db.get(Visitor, visitor_id)
    if not v:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if _.tenant_id and v.tenant_id != _.tenant_id:
        raise HTTPException(status_code=404, detail="Visitor not found")

    # 1. Key events (last 200)
    events = (await db.exec(
        select(TrackingEvent)
        .where(TrackingEvent.visitor_id == visitor_id)
        .order_by(col(TrackingEvent.timestamp).desc())
        .limit(200)
    )).all()

    # 2. Chat sessions
    chats = (await db.exec(
        select(ChatSession)
        .where(ChatSession.visitor_id == visitor_id)
        .order_by(col(ChatSession.started_at).desc())
    )).all()

    # 3. RFQs
    rfqs = (await db.exec(
        select(RFQRequest)
        .where(RFQRequest.visitor_id == visitor_id)
        .order_by(col(RFQRequest.created_at).desc())
    )).all()

    # 4. Chat message previews (first & last message per session) via one batch query
    chat_previews: dict[str, dict] = {}
    chat_ids = [cs.id for cs in chats]
    if chat_ids:
        chat_messages = (await db.exec(
            select(ChatMessage)
            .where(ChatMessage.chat_session_id.in_(chat_ids))  # type: ignore[union-attr]
            .order_by(col(ChatMessage.chat_session_id).asc(), col(ChatMessage.created_at).asc())
        )).all()
        grouped_messages: dict[uuid.UUID, list[ChatMessage]] = {}
        for msg in chat_messages:
            grouped_messages.setdefault(msg.chat_session_id, []).append(msg)

        for chat_id, msgs in grouped_messages.items():
            chat_previews[str(chat_id)] = {
                "first_user_msg": next(
                    (m.content for m in msgs if m.role == "user"), None
                ),
                "last_assistant_msg": next(
                    (m.content for m in reversed(msgs) if m.role == "assistant"), None
                ),
                "total_messages": len(msgs),
            }

    # Build unified timeline entries
    timeline = []

    for e in events:
        timeline.append({
            "type": "event",
            "timestamp": e.timestamp.isoformat(),
            "event_name": e.event_name,
            "page_url": e.page_url,
            "page_type": e.page_type,
            "score_delta": e.score_delta,
            "properties": _json.loads(e.properties) if e.properties else None,
        })

    for cs in chats:
        preview = chat_previews.get(str(cs.id), {})
        timeline.append({
            "type": "chat",
            "timestamp": cs.started_at.isoformat(),
            "chat_session_id": str(cs.id),
            "status": cs.status,
            "message_count": cs.message_count,
            "context_page": cs.context_page,
            "context_entity_type": cs.context_entity_type,
            "quality_rating": cs.quality_rating,
            "first_user_msg": preview.get("first_user_msg"),
            "last_assistant_msg": preview.get("last_assistant_msg"),
        })

    for r in rfqs:
        form = _json.loads(r.form_data) if r.form_data else {}
        timeline.append({
            "type": "rfq",
            "timestamp": r.created_at.isoformat(),
            "rfq_id": str(r.id),
            "rfq_number": r.rfq_number,
            "status": r.status,
            "priority": r.priority,
            "intent_score_at_submit": r.intent_score_at_submit,
            "company_name": form.get("company_name"),
            "email": form.get("email"),
        })

    # Sort by timestamp desc
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)

    # Event breakdown counts
    event_counts = (await db.exec(
        select(TrackingEvent.event_name, func.count(TrackingEvent.event_id).label("c"))
        .where(TrackingEvent.visitor_id == visitor_id)
        .group_by(TrackingEvent.event_name)
    )).all()

    return {
        "visitor": {
            "visitor_id": str(v.visitor_id),
            "intent_score": v.intent_score,
            "intent_stage": v.intent_stage,
            "total_visits": v.total_visits,
            "total_page_views": v.total_page_views,
            "device_type": v.device_type,
            "country": v.country,
            "contact_id": str(v.contact_id) if v.contact_id else None,
            "first_seen": v.first_seen.isoformat(),
            "last_seen": v.last_seen.isoformat(),
        },
        "summary": {
            "total_events": len(events),
            "total_chats": len(chats),
            "total_rfqs": len(rfqs),
            "event_breakdown": {row[0]: row[1] for row in event_counts},
        },
        "timeline": timeline,
    }


# ── Audience Tag endpoints (1b.2.5) ──────────────────────────────────────────

class AudienceTagCreate(BaseModel):
    name: str
    description: str = ""
    rule_type: str = "manual"
    rule_config: dict = {}


@router.get("/audiences")
async def list_audience_tags(
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    rows = (await db.exec(select(AudienceTag).order_by(AudienceTag.name))).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "description": r.description,
            "rule_type": r.rule_type,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/audiences", status_code=status.HTTP_201_CREATED)
async def create_audience_tag(
    body: AudienceTagCreate,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    import json as _json
    existing = (await db.exec(
        select(AudienceTag).where(AudienceTag.name == body.name)
    )).first()
    if existing:
        raise HTTPException(status_code=409, detail="Tag name already exists")
    tag = AudienceTag(
        name=body.name,
        description=body.description,
        rule_type=body.rule_type,
        rule_config=_json.dumps(body.rule_config),
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return {"id": str(tag.id), "name": tag.name}


@router.post("/visitors/{visitor_id}/tags/{tag_id}",
             status_code=status.HTTP_201_CREATED)
async def assign_tag_to_visitor(
    visitor_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    if not await db.get(Visitor, visitor_id):
        raise HTTPException(status_code=404, detail="Visitor not found")
    if not await db.get(AudienceTag, tag_id):
        raise HTTPException(status_code=404, detail="Tag not found")
    existing = (await db.exec(
        select(VisitorTagLink).where(
            VisitorTagLink.visitor_id == visitor_id,
            VisitorTagLink.tag_id == tag_id,
        )
    )).first()
    if existing:
        return {"detail": "Already tagged"}
    db.add(VisitorTagLink(visitor_id=visitor_id, tag_id=tag_id, tagged_by="manual"))
    await db.commit()
    return {"detail": "Tagged"}


@router.delete("/visitors/{visitor_id}/tags/{tag_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def remove_tag_from_visitor(
    visitor_id: uuid.UUID,
    tag_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_content_editor),
):
    link = (await db.exec(
        select(VisitorTagLink).where(
            VisitorTagLink.visitor_id == visitor_id,
            VisitorTagLink.tag_id == tag_id,
        )
    )).first()
    if not link:
        raise HTTPException(status_code=404, detail="Tag link not found")
    await db.delete(link)
    await db.commit()


# ── Remarketing audience members (1b.2.6) ────────────────────────────────────

@router.get("/audiences/{tag_id}/members")
async def get_audience_members(
    tag_id: uuid.UUID,
    limit: int = 200,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Return visitors matching the audience tag's rule_config.

    rule_config JSON schema:
      {
        "event_name": "product_view",   // required: event type to count
        "min_count": 3,                 // optional: minimum event occurrences
        "within_days": 30               // optional: look-back window in days
      }

    For manual tags (rule_type="manual"), returns visitors with the tag
    assigned via POST /tracking/visitors/{id}/tags/{tag_id}.
    For auto_rule tags, dynamically queries the event log.
    """
    import json as _json
    from datetime import timedelta
    from app.models.tracking_event import TrackingEvent

    tag = await db.get(AudienceTag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Audience tag not found")

    if tag.rule_type == "manual":
        # Manual: return visitors with this tag link
        q = (
            select(Visitor)
            .join(VisitorTagLink, VisitorTagLink.visitor_id == Visitor.visitor_id)
            .where(VisitorTagLink.tag_id == tag_id)
            .offset(offset)
            .limit(min(limit, 1000))
        )
        visitors = (await db.exec(q)).all()
        return {
            "tag_id": str(tag_id),
            "tag_name": tag.name,
            "rule_type": "manual",
            "count": len(visitors),
            "members": [_visitor_summary(v) for v in visitors],
        }

    # auto_rule — evaluate rule_config against TrackingEvent log
    try:
        rule = _json.loads(tag.rule_config)
    except (ValueError, TypeError):
        rule = {}

    event_name = rule.get("event_name")
    min_count = int(rule.get("min_count", 1))
    within_days = int(rule.get("within_days", 90))

    if not event_name:
        raise HTTPException(
            status_code=400,
            detail="Audience rule_config must specify 'event_name'"
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)

    # Subquery: count events per visitor matching the rule
    count_subq = (
        select(
            TrackingEvent.visitor_id,
            func.count(TrackingEvent.event_id).label("event_count"),
        )
        .where(
            TrackingEvent.event_name == event_name,
            TrackingEvent.timestamp >= cutoff,
            TrackingEvent.visitor_id.isnot(None),
        )
        .group_by(TrackingEvent.visitor_id)
        .having(func.count(TrackingEvent.event_id) >= min_count)
        .subquery()
    )

    q = (
        select(Visitor)
        .join(count_subq, count_subq.c.visitor_id == Visitor.visitor_id)
        .offset(offset)
        .limit(min(limit, 1000))
    )
    visitors = (await db.exec(q)).all()

    return {
        "tag_id": str(tag_id),
        "tag_name": tag.name,
        "rule_type": "auto_rule",
        "rule": rule,
        "count": len(visitors),
        "members": [_visitor_summary(v) for v in visitors],
    }


def _visitor_summary(v: Visitor) -> dict:
    return {
        "visitor_id": str(v.visitor_id),
        "intent_score": v.intent_score,
        "intent_stage": v.intent_stage,
        "total_visits": v.total_visits,
        "last_seen": v.last_seen.isoformat(),
        "country": v.country,
        "contact_id": str(v.contact_id) if v.contact_id else None,
    }
