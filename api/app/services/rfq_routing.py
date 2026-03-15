"""
RFQ Auto-Routing Service — 1b.4.6

Rules (evaluated in order):
  1. intent_score >= 60 → priority=urgent, assign to senior_sales_user_id
  2. intent_score >= 30 → priority=high
  3. country in HIGH_VALUE_COUNTRIES → priority=high
  4. Default round-robin among active sales users

Config is read from env vars / DB settings for production deployments.
For now, defaults live in ROUTING_RULES below.
"""
import os
import uuid
import logging
from datetime import datetime
from app.core.datetime import utcnow_naive

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session_ctx
from app.models.rfq_request import RFQRequest
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Configurable Rules (override via env or future DB settings table) ─────────

HIGH_VALUE_COUNTRIES = set(
    os.getenv("RFQ_HIGH_VALUE_COUNTRIES", "US,DE,JP,KR,TW,AU,GB,CA,FR,IT").split(",")
)

# Comma-separated UUID strings of users to include in round-robin pool
_SALES_POOL_ENV = os.getenv("RFQ_SALES_POOL", "")
SALES_POOL_IDS: list[str] = [s.strip() for s in _SALES_POOL_ENV.split(",") if s.strip()]


async def route_rfq(rfq_id: uuid.UUID) -> None:
    """
    Determine assigned_to and potentially elevate priority.
    Called asynchronously after RFQ creation — never raises to caller.
    """
    try:
        async with get_session_ctx() as db:
            await _do_route(rfq_id, db)
    except Exception as exc:
        logger.error("rfq_routing error rfq_id=%s: %s", rfq_id, exc)


async def _do_route(rfq_id: uuid.UUID, db: AsyncSession) -> None:
    rfq = await db.get(RFQRequest, rfq_id)
    if not rfq:
        return

    # Elevate priority based on score
    if rfq.intent_score_at_submit >= 60 and rfq.priority != "urgent":
        rfq.priority = "urgent"
    elif rfq.intent_score_at_submit >= 30 and rfq.priority == "normal":
        rfq.priority = "high"

    # Elevate priority based on country
    import json as _json
    if rfq.form_data:
        try:
            country = _json.loads(rfq.form_data).get("country", "")
            if country and country.upper() in HIGH_VALUE_COUNTRIES and rfq.priority == "normal":
                rfq.priority = "high"
        except Exception:
            pass

    # Assign to a sales user from the pool
    if not rfq.assigned_to and SALES_POOL_IDS:
        assigned = await _round_robin_pick(rfq_id, db)
        if assigned:
            rfq.assigned_to = assigned
            rfq.status = "assigned"

    rfq.updated_at = utcnow_naive()
    db.add(rfq)
    await db.commit()


async def _round_robin_pick(rfq_id: uuid.UUID, db: AsyncSession) -> uuid.UUID | None:
    """
    Simple round-robin: pick the pool member with fewest open RFQs.
    Returns None if pool is empty or all users are not found.
    """
    if not SALES_POOL_IDS:
        return None

    from app.models.rfq_request import RFQRequest
    from sqlmodel import func, col

    # Count open RFQs per pool member
    open_statuses = ("new", "assigned", "in_progress")
    counts: dict[uuid.UUID, int] = {}
    for uid_str in SALES_POOL_IDS:
        try:
            uid = uuid.UUID(uid_str)
        except ValueError:
            continue
        count_result = await db.exec(
            select(func.count(RFQRequest.id)).where(
                RFQRequest.assigned_to == uid,
                col(RFQRequest.status).in_(open_statuses),
            )
        )
        counts[uid] = count_result.one()

    if not counts:
        return None

    return min(counts, key=lambda u: counts[u])
