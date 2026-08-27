"""
Intent Score Decay Service — 1b.3.2, 1b.3.3

Spec: visitor intent scores decay over time when no activity occurs.
  - No activity 7 days:  score × 0.8
  - No activity 14 days: score × 0.5
  - No activity 30 days: score × 0.2
  - No activity 60 days: score = 0, stage = "cold"

Stage alert: re-evaluate stage after decay; if stage downgraded, log it.

Run via APScheduler (registered in app startup) or cron trigger.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlmodel import col, select

from app.db.session import get_session_ctx
from app.models.visitor import Visitor
from app.services.intent_scoring import get_intent_stage

logger = logging.getLogger(__name__)

_DECAY_RULES = [
    (60, 0.0),   # >= 60 days → zero
    (30, 0.2),   # >= 30 days → 20 %
    (14, 0.5),   # >= 14 days → 50 %
    (7,  0.8),   # >= 7 days  → 80 %
]


async def run_daily_score_decay() -> dict:
    """
    Process score decay for all visitors whose last activity is overdue.
    Returns summary statistics for logging.
    Returns dict: {processed: N, decayed: N, zeroed: N}
    """
    stats = {"processed": 0, "decayed": 0, "zeroed": 0}
    now = datetime.now(timezone.utc)
    cutoff_date = now - timedelta(days=7)  # only touch stale visitors

    try:
        async with get_session_ctx() as db:
            q = (
                select(Visitor)
                .where(Visitor.intent_score > 0)
                .where(col(Visitor.last_activity_at) < cutoff_date)
                .order_by(col(Visitor.last_activity_at).asc())
                .limit(5000)  # process in batches to avoid OOM
            )
            visitors = (await db.exec(q)).all()
            stats["processed"] = len(visitors)

            for v in visitors:
                old_score = v.intent_score
                new_score = _calculate_decayed_score(v.intent_score, v.last_activity_at, now)
                if new_score != old_score:
                    old_stage = v.intent_stage
                    v.intent_score = new_score
                    v.intent_stage = get_intent_stage(new_score)
                    db.add(v)

                    if new_score == 0:
                        stats["zeroed"] += 1
                    else:
                        stats["decayed"] += 1

                    if old_stage != v.intent_stage:
                        logger.info(
                            "Visitor %s stage downgraded %s→%s after score decay %d→%d",
                            v.visitor_id, old_stage, v.intent_stage, old_score, new_score,
                        )
                        # Notify copilot — fire-and-forget
                        if v.tenant_id:
                            import asyncio

                            from app.services.copilot import on_churn_risk
                            asyncio.create_task(
                                on_churn_risk(v.visitor_id, v.tenant_id, old_stage)
                            )

            await db.commit()
    except Exception:
        logger.exception("Score decay job failed")

    logger.info(
        "Score decay complete: processed=%d decayed=%d zeroed=%d",
        stats["processed"], stats["decayed"], stats["zeroed"],
    )
    return stats


def _calculate_decayed_score(current_score: int, last_activity: datetime, now: datetime) -> int:
    """Return the post-decay score given current score and last activity timestamp."""
    if not last_activity:
        return current_score

    # Ensure timezone-aware comparison
    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    days_inactive = (now - last_activity).days

    for threshold_days, multiplier in _DECAY_RULES:
        if days_inactive >= threshold_days:
            new_score = int(current_score * multiplier)
            return max(0, new_score)

    return current_score
