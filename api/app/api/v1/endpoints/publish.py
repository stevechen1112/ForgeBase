"""
Publish / Unpublish flow  (1a.6.2)

Generic publish/unpublish for all publishable content entities:
  POST /api/v1/content/products/{id}/publish
  POST /api/v1/content/products/{id}/unpublish
  POST /api/v1/content/applications/{id}/publish
  POST /api/v1/content/applications/{id}/unpublish
  POST /api/v1/content/categories/{id}/publish
  POST /api/v1/content/categories/{id}/unpublish
  POST /api/v1/content/faqs/{id}/publish
  POST /api/v1/content/faqs/{id}/unpublish
  POST /api/v1/content/certifications/{id}/publish
  POST /api/v1/content/certifications/{id}/unpublish
  POST /api/v1/content/comparisons/{id}/publish
  POST /api/v1/content/comparisons/{id}/unpublish
  POST /api/v1/content/pages/{id}/publish
  POST /api/v1/content/pages/{id}/unpublish
"""
import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_admin, require_content_editor
from app.core.datetime import utcnow_naive
from app.core.locale import to_content_locale
from app.db.session import get_session
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.faq_item import FAQItem
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.user import User
from app.services.locale_support import contains_cjk, get_source_locale
from app.services.revalidate import revalidate_page
from app.services.translation_draft import SPECS

router = APIRouter(tags=["Publish"])

# Registry: path-prefix → SQLModel class
_PUBLISHABLE: dict[str, Any] = {
    "products": Product,
    "applications": Application,
    "categories": ProductCategory,
    "faqs": FAQItem,
    "certifications": Certification,
    "comparisons": ComparisonTopic,
    "pages": Page,
    "capabilities": Capability,
}


def _ensure_publish_access(obj: Any, user: User) -> None:
    """Reject cross-tenant and legacy-global mutations outside platform staff."""
    if user.is_superuser:
        return
    if not hasattr(obj, "tenant_id"):
        return
    item_tenant_id = getattr(obj, "tenant_id", None)
    if item_tenant_id is None or user.tenant_id is None or item_tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Content not found")


async def _validate_buyer_locale_publish(session: AsyncSession, prefix: str, obj: Any) -> None:
    spec = SPECS.get(prefix)
    if spec is None:
        return
    tenant_id = getattr(obj, "tenant_id", None)
    source_locale = await get_source_locale(session, tenant_id)
    item_locale = to_content_locale(getattr(obj, "locale", None))
    if item_locale == source_locale:
        return
    for field in spec.required_publish_fields:
        value = str(getattr(obj, field, None) or "").strip()
        if not value:
            raise HTTPException(
                status_code=422,
                detail="買方語系尚未填寫必要說明，不能上架。",
            )
        if item_locale == "en" and contains_cjk(value):
            raise HTTPException(
                status_code=422,
                detail="英文版仍含中文內容，請改寫後再上架。",
            )


def _make_publish_routes(prefix: str, Model: Any) -> APIRouter:
    sub = APIRouter(prefix=f"/{prefix}")
    mutation_guard = require_admin if Model is Page else require_content_editor

    def _schedule_revalidate(obj: Any) -> None:
        # 契約 §8：publish/unpublish 後觸發前台 revalidate（目前僅 blog page 有公開快取路徑）
        if not isinstance(obj, Page):
            return
        task = asyncio.create_task(revalidate_page(obj.slug, obj.locale or "en", include_sitemap=True))
        task.add_done_callback(lambda t: None if t.cancelled() else t.exception())

    @sub.post("/{entity_id}/publish")
    async def publish(
        entity_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(mutation_guard),
    ):
        obj = await session.get(Model, entity_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{prefix[:-1].capitalize()} not found")
        _ensure_publish_access(obj, current_user)
        if obj.status == "published":
            return {"detail": "Already published"}
        await _validate_buyer_locale_publish(session, prefix, obj)
        obj.status = "published"
        if hasattr(obj, "published_at"):
            obj.published_at = utcnow_naive()
        if hasattr(obj, "updated_at"):
            obj.updated_at = utcnow_naive()
        session.add(obj)
        await session.commit()
        _schedule_revalidate(obj)
        return {"detail": "Published", "id": str(entity_id)}

    @sub.post("/{entity_id}/unpublish")
    async def unpublish(
        entity_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        current_user: User = Depends(mutation_guard),
    ):
        obj = await session.get(Model, entity_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{prefix[:-1].capitalize()} not found")
        _ensure_publish_access(obj, current_user)
        if obj.status != "published":
            return {"detail": "Not currently published"}
        obj.status = "draft"
        if hasattr(obj, "noindex"):
            obj.noindex = True  # spec 1a.6.2: unpublished pages get noindex
        if hasattr(obj, "updated_at"):
            obj.updated_at = utcnow_naive()
        session.add(obj)
        await session.commit()
        _schedule_revalidate(obj)
        return {"detail": "Unpublished", "id": str(entity_id)}

    return sub


for _prefix, _Model in _PUBLISHABLE.items():
    router.include_router(_make_publish_routes(_prefix, _Model))
