"""
Phase 3.2  ML Intent Scoring Endpoints

3.2.1  POST /tracking/ml/train                          — Train / retrain the ML model
3.2.1  GET  /tracking/ml/status                         — Model status + metadata
3.2.2  GET  /tracking/ml/visitors/{visitor_id}/score    — Predict ML intent score
3.2.2  POST /tracking/ml/visitors/batch-score           — Batch update intent scores for all visitors
3.2.3  GET  /tracking/intent-rules                      — Get current scoring rules (defaults or per-tenant)
3.2.3  PUT  /tracking/intent-rules                      — Update per-tenant scoring rules
"""
import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user, require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.services.intent_scoring import DEFAULT_BASE_SCORES, DEFAULT_STAGES
from app.services.ml_intent import (
    blend_scores,
    get_model_status,
    predict_ml_score,
    train_model,
)
from app.services.retirement_observability import record_retirement_usage

router = APIRouter(tags=["ML Intent Scoring"])


# ── 3.2.3  Intent Scoring Rules ───────────────────────────────────────────────

class StageThreshold(BaseModel):
    min_score: int
    stage: str


class IntentScoringConfig(BaseModel):
    base_scores: dict[str, int]
    stage_thresholds: List[StageThreshold]


def _default_config() -> IntentScoringConfig:
    return IntentScoringConfig(
        base_scores=dict(DEFAULT_BASE_SCORES),
        stage_thresholds=[
            StageThreshold(min_score=t, stage=s) for t, s in DEFAULT_STAGES
        ],
    )


async def _get_site_profile(tenant_id: Optional[uuid.UUID], session: AsyncSession) -> Optional[SiteProfile]:
    stmt = select(SiteProfile)
    if tenant_id:
        stmt = stmt.where(SiteProfile.tenant_id == tenant_id)
    else:
        stmt = stmt.where(SiteProfile.tenant_id.is_(None))
    result = await session.exec(stmt.limit(1))
    return result.first()


@router.get("/tracking/intent-rules", response_model=IntentScoringConfig)
async def get_intent_rules(
    _feature: User = Depends(RequireFeature("advanced_intent_rules")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return current intent scoring rules (custom if set, otherwise system defaults)."""
    profile = await _get_site_profile(current_user.tenant_id, session)
    if profile and profile.intent_scoring_config_json:
        try:
            raw = json.loads(profile.intent_scoring_config_json)
            return IntentScoringConfig(
                base_scores=raw.get("base_scores", DEFAULT_BASE_SCORES),
                stage_thresholds=[
                    StageThreshold(**s) for s in raw.get("stage_thresholds", [])
                ] or _default_config().stage_thresholds,
            )
        except Exception:
            pass
    return _default_config()


@router.put("/tracking/intent-rules", response_model=IntentScoringConfig)
async def update_intent_rules(
    body: IntentScoringConfig,
    _feature: User = Depends(RequireFeature("advanced_intent_rules")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """Save per-tenant intent scoring rules. Changes take effect within 2 minutes."""
    # Validate: all score values must be non-negative integers
    for k, v in body.base_scores.items():
        if not isinstance(v, int) or v < 0:
            raise HTTPException(
                status_code=422,
                detail=f"Score for '{k}' must be a non-negative integer.",
            )
    # Validate: stage thresholds must be descending
    prev = 9999
    for st in body.stage_thresholds:
        if st.min_score > prev:
            raise HTTPException(
                status_code=422,
                detail="stage_thresholds must be in descending order of min_score.",
            )
        prev = st.min_score

    profile = await _get_site_profile(current_user.tenant_id, session)
    if profile is None:
        raise HTTPException(status_code=404, detail="Site profile not found for this tenant.")

    profile.intent_scoring_config_json = json.dumps({
        "base_scores": body.base_scores,
        "stage_thresholds": [s.model_dump() for s in body.stage_thresholds],
    })
    profile.updated_at = utcnow_naive()
    session.add(profile)
    await session.commit()
    return body


# ── 3.2.1  Train Model ────────────────────────────────────────────────────────

@router.post("/tracking/ml/train", status_code=status.HTTP_202_ACCEPTED)
async def train_intent_model(
    background_tasks: BackgroundTasks,
    _feature: User = Depends(RequireFeature("ml_scoring")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """
    Kick off a background ML model training job.
    Uses visitor history + intent events to train a RandomForestClassifier.
    Returns 202 immediately; check /tracking/ml/status for results.
    """
    background_tasks.add_task(train_model, session)
    await record_retirement_usage(
        session,
        candidate_key="ml_scoring_runtime",
        event_name="train",
        tenant_id=current_user.tenant_id,
    )
    return {
        "message": "ML model training started in background.",
        "status_endpoint": "/api/v1/tracking/ml/status",
    }


# ── 3.2.1  Model Status ───────────────────────────────────────────────────────

@router.get("/tracking/ml/status")
async def intent_model_status(
    _feature: User = Depends(RequireFeature("ml_scoring")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Return current ML model status, metadata, and last training details."""
    result = get_model_status()
    await record_retirement_usage(
        session,
        candidate_key="ml_scoring_runtime",
        event_name="status",
        tenant_id=current_user.tenant_id,
    )
    return result


# ── 3.2.2  Predict score for single visitor ───────────────────────────────────

@router.get("/tracking/ml/visitors/{visitor_id}/score")
async def predict_visitor_intent_score(
    visitor_id: uuid.UUID,
    save: bool = Query(False, description="Persist the blended score back to visitors table"),
    _feature: User = Depends(RequireFeature("ml_scoring")),
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
               first_seen, last_activity_at, tenant_id
        FROM visitors WHERE visitor_id = :vid
    """)
    v_result = await session.exec(v_sql, params={"vid": visitor_id})
    visitor_row = v_result.mappings().first()
    if not visitor_row:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if current_user.tenant_id and visitor_row["tenant_id"] != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Visitor not found")

    # Fetch event counts for the visitor
    ev_sql = text("""
        SELECT event_name, COUNT(*) AS cnt
        FROM tracking_events
        WHERE visitor_id = :vid
        GROUP BY event_name
    """)
    ev_result = await session.exec(ev_sql, params={"vid": visitor_id})
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
        await session.exec(
            update_sql,
            params={
                "score": ml_prob * 100,
                "updated_at": utcnow_naive(),
                "vid": visitor_id,
            },
        )
        await session.commit()

    await record_retirement_usage(
        session,
        candidate_key="ml_scoring_runtime",
        event_name="score_and_save" if save else "score_preview",
        tenant_id=current_user.tenant_id,
    )

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
    _feature: User = Depends(RequireFeature("ml_scoring")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """
    Batch-update ml_intent_score for visitors.
    Runs in background. Processes up to `limit` visitors (most recently active first).
    """
    background_tasks.add_task(_run_batch_scoring, limit, current_user.tenant_id)
    await record_retirement_usage(
        session,
        candidate_key="ml_scoring_runtime",
        event_name="batch_score",
        tenant_id=current_user.tenant_id,
    )
    return {
        "message": f"Batch scoring started for up to {limit} visitors.",
        "limit": limit,
    }


async def _run_batch_scoring(limit: int, tenant_id=None) -> None:
    """Background task: score N most recent visitors and persist ml_intent_score.

    Scoped to the triggering user's tenant; tenant_id=None (platform-level
    caller) scores across all tenants.
    """

    from app.db.session import get_session  # avoid circular at module level

    async for session in get_session():
        try:
            visitors_sql = text("""
                SELECT visitor_id, intent_score, intent_stage,
                       total_page_views, total_visits,
                       first_seen, last_activity_at
                FROM visitors
                WHERE (CAST(:tid AS uuid) IS NULL OR tenant_id = CAST(:tid AS uuid))
                ORDER BY last_activity_at DESC NULLS LAST
                LIMIT :lim
            """)
            v_result = await session.exec(
                visitors_sql,
                params={"lim": limit, "tid": str(tenant_id) if tenant_id else None},
            )
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
                    ev_result = await session.exec(ev_sql, params={"vid": vid})
                    event_counts: dict[str, int] = {
                        r["event_name"]: int(r["cnt"]) for r in ev_result.mappings().all()
                    }

                    ml_prob = predict_ml_score(dict(vrow), event_counts)

                    await session.exec(
                        text("""
                            UPDATE visitors
                            SET ml_intent_score = :score,
                                ml_score_updated_at = :updated_at
                            WHERE visitor_id = :vid
                        """),
                        params={
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
