"""Create a buyer-locale draft from a source-locale content row."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, require_user_tenant_id
from app.db.session import get_session
from app.models.user import User
from app.services.translation_draft import SPECS, create_locale_draft

router = APIRouter(tags=["Locale Draft"])
logger = logging.getLogger(__name__)
_CONTENT_EDITOR_ROLES = {"owner", "admin", "marketing_manager"}


def _require_content_editor_role(user: User) -> None:
    if user.role not in _CONTENT_EDITOR_ROLES:
        raise HTTPException(status_code=403, detail="Content editor access required")


class LocaleDraftRequest(BaseModel):
    target_locale: str | None = Field(default=None, max_length=8)


class LocaleDraftBatchRequest(BaseModel):
    entity: str = Field(min_length=1, max_length=30)
    source_ids: list[uuid.UUID] = Field(min_length=1, max_length=25)
    target_locale: str = Field(min_length=2, max_length=8)


@router.post("/locale-drafts/batch")
async def locale_draft_batch(
    payload: LocaleDraftBatchRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(RequireFeature("multilingual")),
) -> dict[str, Any]:
    """Create a bounded set of drafts. Partial failures are explicit and never publish."""
    _require_content_editor_role(current_user)
    if payload.entity not in SPECS:
        raise HTTPException(status_code=422, detail="不支援此內容類型")
    tenant_id = require_user_tenant_id(current_user)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, str | int]] = []
    for source_id in dict.fromkeys(payload.source_ids):
        try:
            results.append(
                await create_locale_draft(
                    session,
                    entity=payload.entity,
                    source_id=source_id,
                    tenant_id=tenant_id,
                    target_locale=payload.target_locale,
                )
            )
        except HTTPException as exc:
            detail = exc.detail
            if isinstance(detail, dict):
                message = str(detail.get("message") or detail.get("error") or detail)
            else:
                message = str(detail)
            failures.append({"source_id": str(source_id), "status_code": exc.status_code, "message": message})
        except Exception:
            await session.rollback()
            logger.exception("batch locale draft failed", extra={"source_id": str(source_id)})
            failures.append({
                "source_id": str(source_id),
                "status_code": 500,
                "message": "建立草稿時發生未預期錯誤",
            })

    return {
        "entity": payload.entity,
        "target_locale": payload.target_locale,
        "requested": len(dict.fromkeys(payload.source_ids)),
        "created_or_updated": len(results),
        "failed": len(failures),
        "results": results,
        "failures": failures,
        "published": 0,
    }


def _make_routes(entity: str) -> APIRouter:
    sub = APIRouter(prefix=f"/{entity}")

    @sub.post("/{entity_id}/locale-draft")
    async def locale_draft(
        entity_id: uuid.UUID,
        payload: LocaleDraftRequest = Body(default_factory=LocaleDraftRequest),
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(RequireFeature("multilingual")),
    ) -> dict[str, Any]:
        _require_content_editor_role(current_user)
        tenant_id = require_user_tenant_id(current_user)
        body = payload
        try:
            return await create_locale_draft(
                session,
                entity=entity,
                source_id=entity_id,
                tenant_id=tenant_id,
                target_locale=body.target_locale,
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail="無法建立語系草稿") from exc

    return sub


for _entity in SPECS:
    router.include_router(_make_routes(_entity))
