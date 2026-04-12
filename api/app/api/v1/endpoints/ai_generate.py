"""
AI content generation endpoint — Epic 1a.4.
POST /content/generate  →  triggers AI generation for a PageBrief.
"""
import json
import logging
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.api.v1.deps import RequireFeature, get_current_user
from app.core.config import settings
from app.models.page_brief import PageBrief
from app.models.product import Product
from app.models.application import Application
from app.models.ai_generation_log import AIGenerationLog
from app.schemas.content import PageBriefRead
from app.services.ai_engine import generate_content, AIGenerationError

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    brief_id: uuid.UUID
    target_locale: str | None = None  # None means use brief.locale


class GenerateResponse(BaseModel):
    brief_id: uuid.UUID
    page_type: str
    result: dict
    log_id: uuid.UUID


@router.post("/generate", response_model=GenerateResponse, tags=["ai"])
async def generate_page_content(
    payload: GenerateRequest,
    _feature=Depends(RequireFeature("ai_content_generation")),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """
    Trigger AI content generation for an approved PageBrief.

    - Brief must be in 'approved' or 'in_progress' status.
    - Fetches related entity data for context.
    - Writes AIGenerationLog and updates brief status on completion.
    """
    brief = await session.get(PageBrief, payload.brief_id)
    if not brief:
        raise HTTPException(status_code=404, detail="PageBrief not found")
    if current_user.tenant_id and brief.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="PageBrief not found")

    if brief.brief_status not in ("approved", "in_progress"):
        raise HTTPException(
            status_code=422,
            detail=f"Brief must be 'approved' or 'in_progress' to generate. Current: '{brief.brief_status}'",
        )

    # Mark as in_progress + processing
    brief.brief_status = "in_progress"
    brief.ai_status = "processing"
    brief.updated_at = utcnow_naive()
    session.add(brief)
    await session.commit()

    # Gather entity context
    entity_data: dict = {}
    entity_id: uuid.UUID | None = None

    if brief.target_page_type == "product" and brief.target_slug:
        from sqlmodel import select
        result = await session.execute(
            select(Product).where(Product.slug == brief.target_slug)
        )
        product = result.scalar_one_or_none()
        if product:
            entity_data = {
                "product_name": product.product_name,
                "model_number": product.model_number,
                "short_description": product.short_description,
                "specifications": product.specifications,
            }
            entity_id = product.id

    elif brief.target_page_type == "application" and brief.target_slug:
        from sqlmodel import select
        result = await session.execute(
            select(Application).where(Application.slug == brief.target_slug)
        )
        application = result.scalar_one_or_none()
        if application:
            entity_data = {
                "application_name": application.application_name,
                "industry": application.industry,
                "description": application.description,
                "challenge": application.challenge,
                "solution": application.solution,
            }
            entity_id = application.id

    brief_dict = {
        "audience_persona": brief.audience_persona,
        "buyer_stage": brief.buyer_stage,
        "primary_keyword": brief.primary_keyword,
        "secondary_keywords": brief.secondary_keywords,
        "tone": brief.tone,
        "word_count_target": brief.word_count_target,
        "notes": brief.notes,
    }

    # Run AI generation
    # target_locale: use request override if provided, else fall back to brief.locale
    effective_locale = payload.target_locale or brief.locale or "en"
    log_id = uuid.uuid4()
    try:
        result_data = await generate_content(
            page_type=brief.target_page_type,
            brief=brief_dict,
            entity_data=entity_data,
            target_locale=effective_locale,
        )

        # Write success log
        log = AIGenerationLog(
            id=log_id,
            brief_id=brief.id,
            triggered_by=current_user.id,
            page_type=brief.target_page_type,
            entity_id=entity_id,
            model_name=settings.AI_MODEL_NAME,
            input_summary=json.dumps({"brief_id": str(brief.id), "entity_id": str(entity_id)}),
            output_json=json.dumps(result_data),
            status="success",
        )
        session.add(log)

        brief.ai_status = "done"
        brief.brief_status = "completed"
        brief.updated_at = utcnow_naive()
        session.add(brief)
        await session.commit()

        logger.info("AI generation succeeded for brief %s", brief.id)
        return GenerateResponse(
            brief_id=brief.id,
            page_type=brief.target_page_type,
            result=result_data,
            log_id=log_id,
        )

    except AIGenerationError as e:
        # Write error log
        log = AIGenerationLog(
            id=log_id,
            brief_id=brief.id,
            triggered_by=current_user.id,
            page_type=brief.target_page_type,
            entity_id=entity_id,
            model_name=settings.AI_MODEL_NAME,
            input_summary=json.dumps({"brief_id": str(brief.id)}),
            status="error",
            error_message=str(e),
        )
        session.add(log)

        brief.ai_status = "error"
        brief.updated_at = utcnow_naive()
        session.add(brief)
        await session.commit()

        logger.error("AI generation failed for brief %s: %s", brief.id, e)
        raise HTTPException(status_code=502, detail=f"AI generation failed: {e}") from e


@router.get("/generate/logs/{brief_id}", tags=["ai"])
async def get_generation_logs(
    brief_id: uuid.UUID,
    _feature=Depends(RequireFeature("ai_content_generation")),
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """Return all AI generation attempts for a brief, newest first."""
    from sqlmodel import select
    result = await session.execute(
        select(AIGenerationLog)
        .where(AIGenerationLog.brief_id == brief_id)
        .order_by(AIGenerationLog.created_at.desc())
    )
    logs = result.scalars().all()
    return {
        "data": [
            {
                "id": str(log.id),
                "brief_id": str(log.brief_id),
                "page_type": log.page_type,
                "model_name": log.model_name,
                "status": log.status,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    }
