"""
Meta-only 修復端點（CF→FB Publish Contract §4.3）

  PATCH /api/v1/content/pages/{id}/meta

僅允許更新 seo_title / seo_description / og_image_url / canonical_url，
送 body／slug／page_type 等欄位一律 422。成功後觸發該 path revalidate。
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.page import Page
from app.models.user import User
from app.schemas.base import APIResponse
from app.schemas.content import PageRead
from app.services.revalidate import revalidate_page
from app.services.trust_content_standards import evaluate_trust_content

router = APIRouter(prefix="/pages", tags=["pages"])


class PageMetaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=160)
    og_image_url: str | None = Field(default=None, max_length=500)
    canonical_url: str | None = Field(default=None, max_length=500)


@router.patch("/{page_id}/meta", response_model=APIResponse)
async def update_page_meta(
    page_id: uuid.UUID,
    payload: PageMetaUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    page = await session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.tenant_id and current_user.tenant_id and page.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Page not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="At least one meta field is required")

    for field, value in updates.items():
        setattr(page, field, value)
    page.updated_at = utcnow_naive()
    session.add(page)
    await session.commit()
    await session.refresh(page)

    task = asyncio.create_task(revalidate_page(page.slug, page.locale or "en"))
    task.add_done_callback(lambda t: None if t.cancelled() else t.exception())

    return APIResponse(data=PageRead.model_validate(page))


@router.get("/{page_id}/trust-check")
async def check_page_trust_standards(
    page_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    """信任內容標準檢查（實效計畫 §4.4）。

    對 certification／capability／case_study／application 類頁面
    回傳逐項 checklist 與分數，可作為 CF 內容 brief 的輸入。
    """
    page = await session.get(Page, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if page.tenant_id and current_user.tenant_id and page.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Page not found")

    result = evaluate_trust_content(page.page_type, page.title or "", page.body or "")
    result["page_id"] = str(page.id)
    result["slug"] = page.slug
    return APIResponse(data=result)
