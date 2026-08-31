"""Transparent, rule-based buyer attention settings."""
from __future__ import annotations

import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user, require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.services.intent_scoring import DEFAULT_BASE_SCORES, DEFAULT_STAGES

router = APIRouter(tags=["Buyer Attention Rules"])


class StageThreshold(BaseModel):
    min_score: int
    stage: str


class IntentScoringConfig(BaseModel):
    base_scores: dict[str, int]
    stage_thresholds: List[StageThreshold]


def _default_config() -> IntentScoringConfig:
    return IntentScoringConfig(
        base_scores=dict(DEFAULT_BASE_SCORES),
        stage_thresholds=[StageThreshold(min_score=value, stage=stage) for value, stage in DEFAULT_STAGES],
    )


async def _site_profile(
    tenant_id: Optional[uuid.UUID], session: AsyncSession
) -> Optional[SiteProfile]:
    statement = select(SiteProfile)
    statement = (
        statement.where(SiteProfile.tenant_id == tenant_id)
        if tenant_id
        else statement.where(SiteProfile.tenant_id.is_(None))
    )
    return (await session.exec(statement.limit(1))).first()


@router.get("/tracking/intent-rules", response_model=IntentScoringConfig)
async def get_intent_rules(
    _feature: User = Depends(RequireFeature("advanced_intent_rules")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    profile = await _site_profile(current_user.tenant_id, session)
    if profile and profile.intent_scoring_config_json:
        try:
            raw = json.loads(profile.intent_scoring_config_json)
            return IntentScoringConfig(
                base_scores=raw.get("base_scores", DEFAULT_BASE_SCORES),
                stage_thresholds=[
                    StageThreshold(**item) for item in raw.get("stage_thresholds", [])
                ] or _default_config().stage_thresholds,
            )
        except (TypeError, ValueError):
            pass
    return _default_config()


@router.put("/tracking/intent-rules", response_model=IntentScoringConfig)
async def update_intent_rules(
    body: IntentScoringConfig,
    _feature: User = Depends(RequireFeature("advanced_intent_rules")),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    for key, value in body.base_scores.items():
        if not isinstance(value, int) or value < 0:
            raise HTTPException(
                status_code=422,
                detail=f"Score for '{key}' must be a non-negative integer.",
            )
    previous = 9999
    for threshold in body.stage_thresholds:
        if threshold.min_score > previous:
            raise HTTPException(
                status_code=422,
                detail="stage_thresholds must be in descending order of min_score.",
            )
        previous = threshold.min_score
    profile = await _site_profile(current_user.tenant_id, session)
    if profile is None:
        raise HTTPException(status_code=404, detail="Site profile not found for this tenant.")
    profile.intent_scoring_config_json = json.dumps(
        {
            "base_scores": body.base_scores,
            "stage_thresholds": [item.model_dump() for item in body.stage_thresholds],
        }
    )
    profile.updated_at = utcnow_naive()
    session.add(profile)
    await session.commit()
    return body
