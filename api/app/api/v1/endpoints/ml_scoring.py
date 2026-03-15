"""
Phase 3.2  ML Intent Scoring Endpoints

3.2.1  POST /tracking/ml/train                          — Train / retrain the ML model
3.2.1  GET  /tracking/ml/status                         — Model status + metadata
3.2.2  GET  /tracking/ml/visitors/{visitor_id}/score    — Predict ML intent score
3.2.2  POST /tracking/ml/visitors/batch-score           — Batch update intent scores for all visitors
"""
import uuid
from typing import Optional

from app.core.datetime import utcnow_naive
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session
from app.models.user import User
from app.services.ml_intent import (
    blend_scores,
    get_model_status,
    predict_ml_score,
    train_model,
)

router = APIRouter(tags=["ML Intent Scoring"])


# ── 3.2.1  Train Model ────────────────────────────────────────────────────────

@router.post("/tracking/ml/train", status_code=status.HTTP_202_ACCEPTED)
async def train_intent_model(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """
    Kick off a background ML model training job.
    Uses visitor history + intent events to train a RandomForestClassifier.
    Returns 202 immediately; check /tracking/ml/status for results.
    """
    background_tasks.add_task(train_model, session)
    return {
        "message": "ML model training started in background.",
        "status_endpoint": "/api/v1/tracking/ml/status",
    }


# ── 3.2.1  Model Status ───────────────────────────────────────────────────────

@router.get("/tracking/ml/status")
async def intent_model_status(
    current_user: User = Depends(get_current_user),
):
    """Return current ML model status, metadata, and last training details."""
    return get_model_status()


# ── 3.2.2  Predict score for single visitor ───────────────────────────────────

@router.get("/tracking/ml/visitors/{visitor_id}/score")
async def predict_visitor_intent_score(
    visitor_id: uuid.UUID,
    save: bool = Query(False, description="Persist the blended score back to visitors table"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Run the ML intent model for a visitor and return a blended score.
    Set `?save=true` to persist the result to the visitor record.
    """
    # Fetch visitor record
    v_sql = text("""
        SELECT visitor_id, intent_score, intent_stage,
               total_page_views, total_visits,
               first_seen, last_activity_at
        FROM visitors WHERE visitor_id = :vid
    """)
    v_result = await session.execute(v_sql, {"vid": visitor_id})
    visitor_row = v_result.mappings().first()
    if not visitor_row:
        raise HTTPException(status_code=404, detail="Visitor not found")

    # Fetch event counts for the visitor
    ev_sql = text("""
        SELECT event_name, COUNT(*) AS cnt
        FROM tracking_events
        WHERE visitor_id = :vid
        GROUP BY event_name
    """)
    ev_result = await session.execute(ev_sql, {"vid": visitor_id})
    event_counts: dict[str, int] = {
        r["event_name"]: int(r["cnt"]) for r in ev_result.mappings().all()
    }

    ml_prob = predict_ml_score(dict(visitor_row), event_counts)
    rule_score = int(visitor_row.get("intent_score") or 0)
    blended = blend_scores(rule_score, ml_prob)

    if save:
        update_sql = text("""
            UPDATE visitors
            SET ml_intent_score = :score,
                ml_score_updated_at = :updated_at
            WHERE visitor_id = :vid
        """)
        await session.execute(
            update_sql,
            {
                "score": ml_prob * 100,
                "updated_at": utcnow_naive(),
                "vid": visitor_id,
            },
        )
        await session.commit()

    return {
        "visitor_id": str(visitor_id),
        "rule_intent_score": rule_score,
        "ml_probability": round(ml_prob, 4),
        "ml_score_pct": round(ml_prob * 100, 1),
        "blended_score": blended,
        "saved": save,
    }


# ── 3.2.2  Batch score all visitors ──────────────────────────────────────────

@router.post("/tracking/ml/visitors/batch-score", status_code=status.HTTP_202_ACCEPTED)
async def batch_score_visitors(
    background_tasks: BackgroundTasks,
    limit: int = Query(500, ge=10, le=5000),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """
    Batch-update ml_intent_score for visitors.
    Runs in background. Processes up to `limit` visitors (most recently active first).
    """
    background_tasks.add_task(_run_batch_scoring, limit)
    return {
        "message": f"Batch scoring started for up to {limit} visitors.",
        "limit": limit,
    }


async def _run_batch_scoring(limit: int) -> None:
    """Background task: score N most recent visitors and persist ml_intent_score."""
    from datetime import datetime

    from app.db.session import get_session  # avoid circular at module level

    async for session in get_session():
        try:
            visitors_sql = text("""
                SELECT visitor_id, intent_score, intent_stage,
                       total_page_views, total_visits,
                       first_seen, last_activity_at
                FROM visitors
                ORDER BY last_activity_at DESC NULLS LAST
                LIMIT :lim
            """)
            v_result = await session.execute(visitors_sql, {"lim": limit})
            rows = v_result.mappings().all()

            for vrow in rows:
                vid = vrow["visitor_id"]
                try:
                    ev_sql = text("""
                        SELECT event_name, COUNT(*) AS cnt
                        FROM tracking_events
                        WHERE visitor_id = :vid
                        GROUP BY event_name
                    """)
                    ev_result = await session.execute(ev_sql, {"vid": vid})
                    event_counts: dict[str, int] = {
                        r["event_name"]: int(r["cnt"]) for r in ev_result.mappings().all()
                    }

                    ml_prob = predict_ml_score(dict(vrow), event_counts)

                    await session.execute(
                        text("""
                            UPDATE visitors
                            SET ml_intent_score = :score,
                                ml_score_updated_at = :updated_at
                            WHERE visitor_id = :vid
                        """),
                        {
                            "score": ml_prob * 100,
                            "updated_at": utcnow_naive(),
                            "vid": vid,
                        },
                    )
                except Exception:
                    continue  # skip individual visitor errors

            await session.commit()
        except Exception:
            pass
