"""
Event Tracking API  (1b.1.2, 1b.1.6, 1b.1.7)

Public endpoint to receive events from the frontend SDK.
Admin endpoint to query events.

POST /tracking/events          — receive a single event (no auth)
POST /tracking/events/batch    — receive up to 20 events at once (no auth)
GET  /tracking/events          — query events (admin auth required)
GET  /tracking/events/summary  — aggregate stats (admin auth required)
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace
from app.core.datetime import utcnow_naive
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)
from sqlmodel import select, col, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user, resolve_tenant_id
from app.db.session import get_session
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.visitor import Visitor
from app.models.contact import Contact
from app.models.user import User
from app.models.content_strategy import ContentStrategy
from app.services.intent_scoring import calculate_score_delta, get_intent_stage, should_alert
from app.services.intent_facets import apply_event_to_visitor, build_intent_explanation
from app.services.notifications import notify_visitor_hot
from app.services.webhook import fire_webhook
from app.services.meta_conversions import fire_meta_event
from app.services.ip_resolver import resolve_ip_to_company

router = APIRouter(prefix="/tracking", tags=["Tracking"])

# ── Per-tenant scoring config cache (TTL = 120s) ──────────────────────────────
import json as _json
import time as _time
_SCORING_CACHE: dict[str, tuple[dict, float]] = {}
_SCORING_CACHE_TTL = 120.0


async def _load_custom_scores(
    tenant_id: Optional[uuid.UUID],
    db: AsyncSession,
) -> Optional[dict[str, int]]:
    """Return per-tenant base_scores if configured, else None (use defaults)."""
    cache_key = str(tenant_id) if tenant_id else "__global__"
    now = _time.monotonic()
    cached = _SCORING_CACHE.get(cache_key)
    if cached is not None:
        config, ts = cached
        if now - ts < _SCORING_CACHE_TTL:
            return config or None

    custom: Optional[dict[str, int]] = None
    try:
        from sqlmodel import select as _sel
        from app.models.site_profile import SiteProfile
        stmt = _sel(SiteProfile)
        if tenant_id:
            stmt = stmt.where(SiteProfile.tenant_id == tenant_id)
        else:
            stmt = stmt.where(SiteProfile.tenant_id.is_(None))
        result = await db.exec(stmt.limit(1))
        profile = result.first()
        if profile and profile.intent_scoring_config_json:
            raw = _json.loads(profile.intent_scoring_config_json)
            custom = raw.get("base_scores") or None
    except Exception:
        pass

    _SCORING_CACHE[cache_key] = (custom, now)
    return custom


# ── Valid event names (spec 12.5.1) ───────────────────────────────────────────

VALID_EVENT_NAMES = {
    "page_view", "category_view", "product_view", "application_view",
    "faq_expand", "comparison_view", "spec_download", "certification_view",
    "cta_click", "form_start", "form_submit", "rfq_start", "rfq_submit",
    "return_visit", "session_depth_reached", "chat_start", "chat_rfq_handoff",
}

# ── Request / Response schemas ────────────────────────────────────────────────

class EventIn(BaseModel):
    event_name: str
    session_id: Optional[uuid.UUID] = None
    visitor_id: Optional[uuid.UUID] = None
    page_url: Optional[str] = None
    page_type: Optional[str] = None
    page_id: Optional[uuid.UUID] = None
    locale: str = "en"
    referrer: Optional[str] = None
    traffic_source: Optional[str] = None
    campaign_id: Optional[str] = None
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    properties: Optional[dict] = None

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        if v not in VALID_EVENT_NAMES:
            raise ValueError(f"Unknown event_name: {v}")
        return v


class EventOut(BaseModel):
    event_id: uuid.UUID
    score_delta: int
    new_intent_score: Optional[int] = None
    new_intent_stage: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return getattr(request.client, "host", None)


async def _upsert_session(
    session_id: uuid.UUID,
    visitor_id: uuid.UUID,
    event: EventIn,
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID] = None,
) -> bool:
    """
    Create or update a tracking session record.
    Returns True if session_depth_reached milestone crossed (page_count just hit 5).
    """
    ts = await db.get(TrackingSession, session_id)
    now = utcnow_naive()
    depth_reached = False
    if ts is None:
        ts = TrackingSession(
            session_id=session_id,
            visitor_id=visitor_id,
            traffic_source=event.traffic_source,
            referrer=event.referrer,
            device_type=event.device_type,
            entry_page=event.page_url,
            tenant_id=tenant_id,
        )
        if event.campaign_id:
            # Parse UTM params if campaign_id is a JSON string or plain string
            try:
                utms = json.loads(event.campaign_id)
                ts.utm_source = utms.get("utm_source")
                ts.utm_medium = utms.get("utm_medium")
                ts.utm_campaign = utms.get("utm_campaign")
                ts.utm_term = utms.get("utm_term")
                ts.utm_content = utms.get("utm_content")
            except (json.JSONDecodeError, TypeError):
                ts.utm_campaign = event.campaign_id
    prev_count = ts.page_count
    ts.page_count += 1
    ts.end_time = now
    ts.exit_page = event.page_url or ts.exit_page
    ts.updated_at = now
    db.add(ts)
    # Milestone: crossing 5 pages triggers session_depth_reached
    if prev_count < 5 <= ts.page_count:
        depth_reached = True
    return depth_reached


async def _upsert_visitor(
    visitor_id: uuid.UUID,
    event: EventIn,
    db: AsyncSession,
    score_delta: int,
    client_ip: Optional[str] = None,
    tenant_id: Optional[uuid.UUID] = None,
) -> tuple[int, str, str, bool]:
    """
    Create or update visitor record. Apply score_delta.
    Returns (new_score, old_stage, new_stage, is_return_visit).
    is_return_visit is True when visitor existed and last_seen > 24h ago.
    """
    visitor = await db.get(Visitor, visitor_id)
    now = utcnow_naive()
    is_return_visit = False
    if visitor is None:
        visitor = Visitor(
            visitor_id=visitor_id,
            device_type=event.device_type,
            tenant_id=tenant_id,
        )
    else:
        # Return visit detection: same visitor, gap > 24 hours
        last_seen_naive = visitor.last_seen.replace(tzinfo=None) if visitor.last_seen.tzinfo is not None else visitor.last_seen
        if (now - last_seen_naive) > timedelta(hours=24):
            is_return_visit = True
            visitor.total_visits += 1

    old_stage = visitor.intent_stage
    old_score = visitor.intent_score
    new_score = max(0, old_score + score_delta)

    visitor.intent_score = new_score
    visitor.last_seen = now
    visitor.last_activity_at = now
    visitor.updated_at = now

    if event.page_type == "product" or event.event_name == "page_view":
        visitor.total_page_views += 1
    if event.device_type and not visitor.device_type:
        visitor.device_type = event.device_type

    new_stage = get_intent_stage(new_score)
    stage_changed = new_stage != old_stage
    if stage_changed:
        visitor.intent_stage = new_stage
        visitor.stage_alert_sent = False  # Reset so alert can fire

    # Intent Score 2.0 facets（§4.1）：事件 facet 累積
    apply_event_to_visitor(visitor, event.event_name, score_delta, event.page_type)

    db.add(visitor)
    # Note: explicit flush moved to receive_event after all upserts

    # Nurture trigger: linked contact reaching a triggered intent stage (§2.1.4)
    if stage_changed and visitor.intent_stage in ("warm", "hot", "sales_ready"):
        try:
            from app.services.subscription import get_plan_feature
            plan_ok = True
            if tenant_id:
                from app.models.tenant import Tenant
                tenant = await db.get(Tenant, tenant_id)
                plan_ok = bool(tenant and get_plan_feature(tenant.plan, "nurture_email"))
            if plan_ok:
                cq = select(Contact).where(Contact.visitor_id == visitor.visitor_id)
                if tenant_id:
                    cq = cq.where(Contact.tenant_id == tenant_id)
                contact = (await db.exec(cq)).first()
                if contact:
                    from app.api.v1.endpoints.nurture import trigger_nurture_for_contact
                    await trigger_nurture_for_contact(
                        contact.id, "intent_stage", visitor.intent_stage, tenant_id=tenant_id
                    )
        except Exception:
            logger.exception("Nurture auto-enroll failed for visitor %s", visitor.visitor_id)

    return new_score, old_stage, new_stage, is_return_visit


async def _refresh_intent_explanation(
    visitor_id: uuid.UUID,
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID],
    current_event: Optional[EventIn] = None,
) -> None:
    """依近期事件重建「為何 Hot」解釋字串（§4.1 輸出要求）。"""
    visitor = await db.get(Visitor, visitor_id)
    if not visitor:
        return
    q = (
        select(TrackingEvent)
        .where(TrackingEvent.visitor_id == visitor_id)
        .order_by(col(TrackingEvent.timestamp).desc())
        .limit(50)
    )
    if tenant_id:
        q = q.where(TrackingEvent.tenant_id == tenant_id)
    events = list((await db.exec(q)).all())
    if current_event is not None:
        # 當前事件尚未落庫，手動附加（置頂，視為最新）
        events.insert(0, SimpleNamespace(
            event_name=current_event.event_name,
            page_type=current_event.page_type,
            created_at=utcnow_naive(),
        ))
    # 與 has_rfq 一致：表單建立的 RFQ 不一定有 rfq_submit 事件
    from app.models.rfq_request import RFQRequest
    rfq_q = select(RFQRequest.id).where(RFQRequest.visitor_id == visitor_id).limit(1)
    if tenant_id:
        rfq_q = rfq_q.where(RFQRequest.tenant_id == tenant_id)
    has_rfq_record = (await db.exec(rfq_q)).first() is not None
    visitor.intent_explanation = build_intent_explanation(
        events, now=utcnow_naive(), has_rfq_record=has_rfq_record,
    ) or None
    db.add(visitor)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/events", response_model=EventOut, status_code=status.HTTP_202_ACCEPTED)
async def receive_event(
    body: EventIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    """
    Receive a single tracking event from the frontend SDK.
    No authentication required — public endpoint.
    Applies intent scoring to the visitor.
    """
    props = body.properties or {}
    custom_scores = await _load_custom_scores(tenant_id, db)
    score_delta = calculate_score_delta(body.event_name, props, custom_scores=custom_scores)
    client_ip = _get_client_ip(request)

    new_score: Optional[int] = None
    new_stage: Optional[str] = None
    old_stage: str = "cold"
    computed_events: list[str] = []

    # Upsert session if IDs are provided
    if body.session_id and body.visitor_id:
        # Visitor must be upserted FIRST to satisfy FK constraint on tracking_sessions
        new_score, old_stage, new_stage, is_return = await _upsert_visitor(
            body.visitor_id, body, db, score_delta, client_ip, tenant_id
        )
        depth_reached = await _upsert_session(body.session_id, body.visitor_id, body, db, tenant_id)
        if is_return:
            computed_events.append("return_visit")
        if depth_reached:
            computed_events.append("session_depth_reached")
    elif body.visitor_id:
        new_score, old_stage, new_stage, is_return = await _upsert_visitor(
            body.visitor_id, body, db, score_delta, client_ip, tenant_id
        )
        if is_return:
            computed_events.append("return_visit")

    # Flush visitor/session to DB before inserting events (FK constraint)
    if body.visitor_id:
        await db.flush()

    # Record the primary event
    event_obj = TrackingEvent(
        event_name=body.event_name,
        session_id=body.session_id,
        visitor_id=body.visitor_id,
        page_url=body.page_url,
        page_type=body.page_type,
        page_id=body.page_id,
        locale=body.locale,
        referrer=body.referrer,
        traffic_source=body.traffic_source,
        campaign_id=body.campaign_id,
        user_agent=body.user_agent,
        device_type=body.device_type,
        ip_address=client_ip,
        properties=json.dumps(props) if props else None,
        score_delta=score_delta,
        tenant_id=tenant_id,
    )
    db.add(event_obj)

    # Insert computed events with their own score deltas
    for computed_name in computed_events:
        c_delta = calculate_score_delta(computed_name, {})
        if new_score is not None:
            visitor_obj = await db.get(Visitor, body.visitor_id)
            if visitor_obj:
                visitor_obj.intent_score = max(0, visitor_obj.intent_score + c_delta)
                new_score = visitor_obj.intent_score
                new_stage = get_intent_stage(new_score)
                visitor_obj.intent_stage = new_stage
                db.add(visitor_obj)
        db.add(TrackingEvent(
            event_name=computed_name,
            session_id=body.session_id,
            visitor_id=body.visitor_id,
            page_url=body.page_url,
            page_type=body.page_type,
            locale=body.locale,
            device_type=body.device_type,
            ip_address=client_ip,
            score_delta=c_delta,
            tenant_id=tenant_id,
        ))

    await db.flush()
    if body.visitor_id:
        await _refresh_intent_explanation(body.visitor_id, db, tenant_id)
    await db.commit()

    # 1b.3.5 Intent trigger: fire sales alert on stage escalation to hot/sales_ready
    if body.visitor_id and new_score is not None and new_stage in ("hot", "sales_ready"):
        if should_alert(old_stage, new_stage):
            asyncio.create_task(notify_visitor_hot(body.visitor_id, new_stage, new_score))
            # Copilot hot visitor notification
            if tenant_id:
                from app.services.copilot import on_hot_visitor as _copilot_hot
                asyncio.create_task(_copilot_hot(body.visitor_id, tenant_id))
            # 1b.5.3 visitor.became_hot webhook
            fire_webhook("visitor.became_hot", {
                "visitor_id":   str(body.visitor_id),
                "intent_stage": new_stage,
                "intent_score": new_score,
                "page_url":     body.page_url,
            })
            # 1b.5.3 contact.intent_stage_changed webhook (if visitor has linked contact)
            try:
                visitor_for_hook = await db.get(Visitor, body.visitor_id)
                if visitor_for_hook and visitor_for_hook.contact_id:
                    fire_webhook("contact.intent_stage_changed", {
                        "visitor_id":  str(body.visitor_id),
                        "contact_id":  str(visitor_for_hook.contact_id),
                        "old_stage":   old_stage,
                        "new_stage":   new_stage,
                        "intent_score": new_score,
                    })
                    # Nurture engine removed
            except Exception:
                logger.warning("visitor intent stage webhook failed", exc_info=True)

    # 1b.5.5 Meta Conversions API — fire server-side event for mapped event types
    if body.visitor_id:
        asyncio.create_task(fire_meta_event(
            event_name=body.event_name,
            visitor_id=str(body.visitor_id),
            page_url=body.page_url,
            ip_address=client_ip,
            user_agent=body.user_agent,
            event_id=str(event_obj.event_id),
        ))

    return EventOut(
        event_id=event_obj.event_id,
        score_delta=score_delta,
        new_intent_score=new_score,
        new_intent_stage=new_stage,
    )


@router.post("/events/batch", status_code=status.HTTP_202_ACCEPTED)
async def receive_events_batch(
    body: list[EventIn],
    request: Request,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    """Receive up to 20 events at once (e.g. queued while offline)."""
    if len(body) > 20:
        raise HTTPException(status_code=400, detail="Max 20 events per batch")
    results = []
    for ev in body:
        props = ev.properties or {}
        score_delta = calculate_score_delta(ev.event_name, props)
        new_score = None
        new_stage = None
        if ev.session_id and ev.visitor_id:
            # Visitor MUST be upserted first to satisfy FK on tracking_sessions
            new_score, _, new_stage, _ = await _upsert_visitor(
                ev.visitor_id, ev, db, score_delta, tenant_id=tenant_id
            )
            await db.flush()
            await _upsert_session(ev.session_id, ev.visitor_id, ev, db, tenant_id)
            await db.flush()  # Also flush session before inserting event (fk_events_session_id)
        elif ev.visitor_id:
            new_score, _, new_stage, _ = await _upsert_visitor(
                ev.visitor_id, ev, db, score_delta, tenant_id=tenant_id
            )
        event_obj = TrackingEvent(
            event_name=ev.event_name,
            session_id=ev.session_id,
            visitor_id=ev.visitor_id,
            page_url=ev.page_url,
            page_type=ev.page_type,
            page_id=ev.page_id,
            locale=ev.locale,
            referrer=ev.referrer,
            traffic_source=ev.traffic_source,
            campaign_id=ev.campaign_id,
            user_agent=ev.user_agent,
            device_type=ev.device_type,
            ip_address=_get_client_ip(request),
            properties=json.dumps(props) if props else None,
            score_delta=score_delta,
            tenant_id=tenant_id,
        )
        db.add(event_obj)
        results.append({
            "event_id": str(event_obj.event_id),
            "score_delta": score_delta,
            "new_intent_stage": new_stage,
        })
    # 與單筆路徑一致：batch 結束後為每位訪客刷新「為何 Hot」
    await db.flush()
    refreshed: set[uuid.UUID] = set()
    for ev in body:
        if ev.visitor_id and ev.visitor_id not in refreshed:
            refreshed.add(ev.visitor_id)
            await _refresh_intent_explanation(ev.visitor_id, db, tenant_id)
    await db.commit()
    return {"processed": len(results), "results": results}


# ── Admin query endpoints ─────────────────────────────────────────────────────

@router.get("/events", response_model=list[dict])
async def query_events(
    visitor_id: Optional[uuid.UUID] = None,
    session_id: Optional[uuid.UUID] = None,
    event_name: Optional[str] = None,
    page_type: Optional[str] = None,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Query events with filters. Admin only."""
    q = select(TrackingEvent).order_by(col(TrackingEvent.timestamp).desc())
    if _.tenant_id:
        q = q.where(TrackingEvent.tenant_id == _.tenant_id)
    if visitor_id:
        q = q.where(TrackingEvent.visitor_id == visitor_id)
    if session_id:
        q = q.where(TrackingEvent.session_id == session_id)
    if event_name:
        q = q.where(TrackingEvent.event_name == event_name)
    if page_type:
        q = q.where(TrackingEvent.page_type == page_type)
    if from_ts:
        q = q.where(TrackingEvent.timestamp >= from_ts)
    if to_ts:
        q = q.where(TrackingEvent.timestamp <= to_ts)
    q = q.offset(offset).limit(min(limit, 500))
    rows = (await db.exec(q)).all()
    return [
        {
            "event_id": str(r.event_id),
            "event_name": r.event_name,
            "timestamp": r.timestamp.isoformat(),
            "visitor_id": str(r.visitor_id) if r.visitor_id else None,
            "session_id": str(r.session_id) if r.session_id else None,
            "page_url": r.page_url,
            "page_type": r.page_type,
            "traffic_source": r.traffic_source,
            "device_type": r.device_type,
            "country": r.country,
            "score_delta": r.score_delta,
            "properties": json.loads(r.properties) if r.properties else None,
        }
        for r in rows
    ]


@router.get("/events/summary")
async def events_summary(
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """Aggregate event counts grouped by event_name."""
    q = (
        select(TrackingEvent.event_name, func.count(TrackingEvent.event_id).label("count"))
        .group_by(TrackingEvent.event_name)
        .order_by(func.count(TrackingEvent.event_id).desc())
    )
    if _.tenant_id:
        q = q.where(TrackingEvent.tenant_id == _.tenant_id)
    if from_ts:
        q = q.where(TrackingEvent.timestamp >= from_ts)
    if to_ts:
        q = q.where(TrackingEvent.timestamp <= to_ts)
    rows = (await db.exec(q)).all()
    return [{"event_name": r[0], "count": r[1]} for r in rows]


# ── 2.5.1 Page-level analytics ────────────────────────────────────────────────

@router.get("/events/pages")
async def events_by_page(
    days: int = 30,
    page_type: Optional[str] = None,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Returns per-page aggregated view counts and unique visitor counts.
    Filters to page_view events within the last `days` days.
    """
    since = utcnow_naive() - timedelta(days=days)
    q = (
        select(
            TrackingEvent.page_type,
            TrackingEvent.page_id,
            TrackingEvent.page_url,
            func.count(TrackingEvent.event_id).label("views"),
            func.count(func.distinct(TrackingEvent.visitor_id)).label("unique_visitors"),
        )
        .where(
            TrackingEvent.event_name == "page_view",
            TrackingEvent.timestamp >= since,
            TrackingEvent.page_url.is_not(None),
        )
        .group_by(
            TrackingEvent.page_type,
            TrackingEvent.page_id,
            TrackingEvent.page_url,
        )
        .order_by(func.count(TrackingEvent.event_id).desc())
    )
    if _.tenant_id:
        q = q.where(TrackingEvent.tenant_id == _.tenant_id)
    if page_type:
        q = q.where(TrackingEvent.page_type == page_type)
    rows = (await db.exec(q)).all()
    return [
        {
            "page_type": r[0],
            "page_id": str(r[1]) if r[1] else None,
            "page_url": r[2],
            "views": r[3],
            "unique_visitors": r[4],
        }
        for r in rows
    ]


# ── 2.5.2 Entity-level analytics (product / application) ─────────────────────

@router.get("/events/entities")
async def events_by_entity(
    days: int = 30,
    page_type: Optional[str] = None,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Returns per-entity event totals — views, RFQ starts, spec downloads.
    Useful for product and application performance dashboards (2.5.2).
    """
    since = utcnow_naive() - timedelta(days=days)
    q = (
        select(
            TrackingEvent.page_type,
            TrackingEvent.page_id,
            TrackingEvent.page_url,
            TrackingEvent.event_name,
            func.count(TrackingEvent.event_id).label("count"),
        )
        .where(
            TrackingEvent.timestamp >= since,
            TrackingEvent.page_id.is_not(None),
            TrackingEvent.event_name.in_(["page_view", "rfq_start", "rfq_submit", "spec_download", "cta_click"]),
        )
        .group_by(
            TrackingEvent.page_type,
            TrackingEvent.page_id,
            TrackingEvent.page_url,
            TrackingEvent.event_name,
        )
        .order_by(TrackingEvent.page_id, TrackingEvent.event_name)
    )
    if _.tenant_id:
        q = q.where(TrackingEvent.tenant_id == _.tenant_id)
    if page_type:
        q = q.where(TrackingEvent.page_type == page_type)
    rows = (await db.exec(q)).all()

    # Pivot: group by entity, event → count
    entities: dict[str, dict] = {}
    for r in rows:
        key = str(r[1])
        if key not in entities:
            entities[key] = {
                "page_type": r[0],
                "page_id": key,
                "page_url": r[2],
                "page_view": 0,
                "rfq_start": 0,
                "rfq_submit": 0,
                "spec_download": 0,
                "cta_click": 0,
            }
        entities[key][r[3]] = r[4]

    return sorted(entities.values(), key=lambda x: x["page_view"], reverse=True)


# ── 2.5.3 Strategy map performance view ──────────────────────────────────────

@router.get("/events/strategy-performance")
async def strategy_performance(
    days: int = 30,
    _feature: User = Depends(RequireFeature("full_tracking")),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
):
    """
    Joins ContentStrategy entries with aggregated TrackingEvent data
    to show performance metrics per strategy map entry.
    """
    since = utcnow_naive() - timedelta(days=days)

    # Aggregate events by page_id
    event_q = (
        select(
            TrackingEvent.page_id,
            TrackingEvent.event_name,
            func.count(TrackingEvent.event_id).label("count"),
        )
        .where(
            TrackingEvent.timestamp >= since,
            TrackingEvent.page_id.is_not(None),
        )
        .group_by(TrackingEvent.page_id, TrackingEvent.event_name)
    )
    if _.tenant_id:
        event_q = event_q.where(TrackingEvent.tenant_id == _.tenant_id)
    event_rows = (await db.exec(event_q)).all()

    # Build lookup: {page_id → {event_name → count}}
    perf: dict[str, dict[str, int]] = {}
    for row in event_rows:
        key = str(row[0])
        perf.setdefault(key, {"page_view": 0, "rfq_start": 0, "rfq_submit": 0, "spec_download": 0})
        if row[1] in perf[key]:
            perf[key][row[1]] = row[2]

    # Load all strategy entries
    strategy_q = select(ContentStrategy)
    if _.tenant_id:
        strategy_q = strategy_q.where(ContentStrategy.tenant_id == _.tenant_id)
    strategies = (await db.exec(strategy_q)).all()

    return [
        {
            "id": str(s.id),
            "page_type": s.page_type,
            "entity_type": s.entity_type,
            "entity_id": str(s.entity_id) if s.entity_id else None,
            "status": s.status,
            "locale": s.locale,
            "notes": s.notes,
            # Performance overlay
            **perf.get(str(s.entity_id) if s.entity_id else "", {
                "page_view": 0, "rfq_start": 0, "rfq_submit": 0, "spec_download": 0
            }),
        }
        for s in strategies
    ]
