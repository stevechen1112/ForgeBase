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
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.application import Application
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.faq_item import FAQItem
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.user import User

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
}


def _make_publish_routes(prefix: str, Model: Any) -> APIRouter:
    sub = APIRouter(prefix=f"/{prefix}")

    @sub.post("/{entity_id}/publish")
    async def publish(
        entity_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        _: User = Depends(require_content_editor),
    ):
        obj = await session.get(Model, entity_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{prefix[:-1].capitalize()} not found")
        if obj.status == "published":
            return {"detail": "Already published"}
        obj.status = "published"
        if hasattr(obj, "published_at"):
            obj.published_at = utcnow_naive()
        if hasattr(obj, "updated_at"):
            obj.updated_at = utcnow_naive()
        session.add(obj)
        await session.commit()
        return {"detail": "Published", "id": str(entity_id)}

    @sub.post("/{entity_id}/unpublish")
    async def unpublish(
        entity_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        _: User = Depends(require_content_editor),
    ):
        obj = await session.get(Model, entity_id)
        if not obj:
            raise HTTPException(status_code=404, detail=f"{prefix[:-1].capitalize()} not found")
        if obj.status != "published":
            return {"detail": "Not currently published"}
        obj.status = "draft"
        if hasattr(obj, "noindex"):
            obj.noindex = True  # spec 1a.6.2: unpublished pages get noindex
        if hasattr(obj, "updated_at"):
            obj.updated_at = utcnow_naive()
        session.add(obj)
        await session.commit()
        return {"detail": "Unpublished", "id": str(entity_id)}

    return sub


for _prefix, _Model in _PUBLISHABLE.items():
    router.include_router(_make_publish_routes(_prefix, _Model))
