"""
Translation Draft endpoint — LLM-assisted locale drafting.

POST /api/v1/content/translate-draft

Given a source entity id + target locale, returns a translated draft of the
entity's whitelisted text fields. Nothing is persisted: the admin reviews the
draft in the create form and saves manually. This is a drafting aid, not an
auto-translation pipeline.
"""
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user
from app.db.session import get_session
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.faq_item import FAQItem
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.services.translator import (
    SOURCE_LOCALE,
    SUPPORTED_TARGETS,
    TRANSLATABLE_FIELDS,
    TranslationError,
    load_glossary,
    translate_fields,
    translate_specifications,
)
from sqlmodel import select

router = APIRouter(tags=["Content: Translate"])

ENTITY_MODELS: dict[str, type] = {
    "product": Product,
    "category": ProductCategory,
    "application": Application,
    "faq": FAQItem,
    "certification": Certification,
    "capability": Capability,
    "comparison": ComparisonTopic,
    "page": Page,
}


class TranslateDraftRequest(BaseModel):
    entity_type: str = Field(description="One of: " + ", ".join(sorted(ENTITY_MODELS)))
    source_id: uuid.UUID
    target_locale: str = Field(default="zh-tw", max_length=5)


class TranslateDraftResponse(BaseModel):
    entity_type: str
    source_id: uuid.UUID
    source_locale: str
    target_locale: str
    slug: Optional[str] = None
    fields: dict[str, Any]
    glossary_applied: int


async def _load_glossary(db: AsyncSession, tenant_id: Optional[uuid.UUID]) -> list[dict[str, str]]:
    stmt = select(SiteProfile)
    stmt = stmt.where(SiteProfile.tenant_id == tenant_id) if tenant_id else stmt.where(SiteProfile.tenant_id.is_(None))
    profile = (await db.exec(stmt.limit(1))).first()
    return load_glossary(profile.translation_glossary_json if profile else None)


@router.post("/translate-draft", response_model=TranslateDraftResponse)
async def translate_draft(
    payload: TranslateDraftRequest,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    _feature: User = Depends(RequireFeature("multilingual")),
):
    # 租戶隔離以登入者為準，不信任 X-Tenant-ID 標頭（與 content_crud 同規則）
    tenant_id: Optional[uuid.UUID] = current_user.tenant_id

    model = ENTITY_MODELS.get(payload.entity_type)
    if model is None:
        raise HTTPException(status_code=422, detail=f"Unsupported entity_type: {payload.entity_type}")
    if payload.target_locale not in SUPPORTED_TARGETS:
        raise HTTPException(status_code=422, detail=f"Unsupported target_locale: {payload.target_locale}")

    entity = await db.get(model, payload.source_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Source entity not found")
    # Tenant isolation: same rule as content_crud._ensure_item_access
    entity_tenant = getattr(entity, "tenant_id", None)
    if hasattr(entity, "tenant_id"):
        if tenant_id is None and entity_tenant is not None:
            raise HTTPException(status_code=404, detail="Source entity not found")
        if tenant_id is not None and entity_tenant != tenant_id:
            raise HTTPException(status_code=404, detail="Source entity not found")
    if getattr(entity, "locale", SOURCE_LOCALE) != SOURCE_LOCALE:
        raise HTTPException(
            status_code=422,
            detail=f"Source entity locale is '{getattr(entity, 'locale', '?')}', expected '{SOURCE_LOCALE}'",
        )

    source_fields = {
        name: getattr(entity, name, None)
        for name in TRANSLATABLE_FIELDS[payload.entity_type]
    }
    glossary = await _load_glossary(db, tenant_id)

    try:
        translated = await translate_fields(
            payload.entity_type, source_fields, payload.target_locale, glossary
        )
        if payload.entity_type == "product" and getattr(entity, "specifications", None):
            translated["specifications"] = await translate_specifications(
                entity.specifications, payload.target_locale, glossary
            )
    except TranslationError as e:
        raise HTTPException(status_code=502, detail=f"翻譯服務暫時不可用：{e}") from e

    return TranslateDraftResponse(
        entity_type=payload.entity_type,
        source_id=payload.source_id,
        source_locale=SOURCE_LOCALE,
        target_locale=payload.target_locale,
        slug=getattr(entity, "slug", None),
        fields=translated,
        glossary_applied=len(glossary),
    )
