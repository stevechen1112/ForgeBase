"""
Remaining content CRUD endpoints:
  /api/v1/content/applications
  /api/v1/content/faqs
  /api/v1/content/comparisons
  /api/v1/content/certifications
  /api/v1/content/capabilities
  /api/v1/content/ctas
  /api/v1/content/pages
  /api/v1/content/briefs
"""
import uuid
from typing import Type, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from slugify import slugify

from app.api.v1.deps import get_current_user, require_admin, require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.application import Application
from app.models.faq_item import FAQItem
from app.models.comparison_topic import ComparisonTopic
from app.models.certification import Certification
from app.models.capability import Capability
from app.models.cta import CTA
from app.models.page import Page
from app.models.page_brief import PageBrief
from app.schemas.base import APIResponse, PaginationMeta
from app.schemas.content import (
    ApplicationCreate, ApplicationRead, ApplicationUpdate,
    FAQItemCreate, FAQItemRead, FAQItemUpdate,
    ComparisonTopicCreate, ComparisonTopicRead, ComparisonTopicUpdate,
    CertificationCreate, CertificationRead, CertificationUpdate,
    CapabilityCreate, CapabilityRead, CapabilityUpdate,
    CTACreate, CTARead, CTAUpdate,
    PageCreate, PageRead, PageUpdate,
    PageBriefCreate, PageBriefRead, PageBriefUpdate,
)


# ── Generic CRUD factory ──────────────────────────────────────────────────────
def build_slug(payload: Any, slug_field: str | None) -> str | None:
    if not slug_field:
        return None

    existing = getattr(payload, slug_field, None)
    if existing:
        return existing

    for source_field in (
        "cert_name",
        "capability_name",
        "application_name",
        "topic_title",
        "category_name",
        "product_name",
        "title",
    ):
        source_value = getattr(payload, source_field, None)
        if source_value:
            return slugify(source_value, lowercase=True, separator="-")[:120]

    return None


def make_crud_router(
    prefix: str,
    tag: str,
    Model,
    ReadSchema,
    CreateSchema,
    UpdateSchema,
    slug_field: str | None = "slug",
    locale_filter: bool = True,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", response_model=APIResponse)
    async def list_items(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        item_status: str | None = Query(None, alias="status"),
        locale: str | None = Query(None),
        slug: str | None = Query(None),
        session: AsyncSession = Depends(get_session),
    ):
        base_q = select(Model)
        if locale_filter and hasattr(Model, "locale") and locale:
            base_q = base_q.where(Model.locale == locale)
        if item_status and hasattr(Model, "status"):
            base_q = base_q.where(Model.status == item_status)
        if slug and hasattr(Model, "slug"):
            base_q = base_q.where(Model.slug == slug)

        total = (await session.exec(select(func.count()).select_from(base_q.subquery()))).one()
        order_col = getattr(Model, "sort_order", None) or getattr(Model, "created_at")
        items_q = base_q.order_by(order_col).offset((page - 1) * page_size).limit(page_size)
        items = (await session.exec(items_q)).all()

        return APIResponse(
            data=[ReadSchema.model_validate(i) for i in items],
            meta=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=(total + page_size - 1) // page_size,
            ),
        )

    @router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
    async def create_item(
        payload: CreateSchema,  # type: ignore[valid-type]
        session: AsyncSession = Depends(get_session),
        _user=Depends(require_content_editor),
    ):
        generated_slug = build_slug(payload, slug_field)
        if slug_field:
            slug_val = generated_slug
            if slug_val:
                # if model has locale, uniqueness is per (slug, locale)
                locale_val = getattr(payload, "locale", None)
                if locale_val and hasattr(Model, "locale"):
                    existing = await session.exec(
                        select(Model).where(
                            getattr(Model, slug_field) == slug_val,
                            Model.locale == locale_val,
                        )
                    )
                else:
                    existing = await session.exec(
                        select(Model).where(getattr(Model, slug_field) == slug_val)
                    )
                if existing.first():
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")

        dump = payload.model_dump()
        if slug_field and generated_slug:
            dump[slug_field] = generated_slug
        # inject created_by for PageBrief
        if hasattr(Model, "created_by") and _user:
            dump["created_by"] = _user.id

        item = Model(**dump)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return APIResponse(data=ReadSchema.model_validate(item))

    @router.get("/{item_id}", response_model=APIResponse)
    async def get_item(
        item_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
    ):
        item = await session.get(Model, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        return APIResponse(data=ReadSchema.model_validate(item))

    @router.patch("/{item_id}", response_model=APIResponse)
    async def update_item(
        item_id: uuid.UUID,
        payload: UpdateSchema,  # type: ignore[valid-type]
        session: AsyncSession = Depends(get_session),
        _user=Depends(require_content_editor),
    ):
        item = await session.get(Model, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

        updates = payload.model_dump(exclude_unset=True)
        if slug_field and slug_field in updates:
            new_slug = updates[slug_field]
            if new_slug != getattr(item, slug_field):
                # if model has locale, uniqueness is per (slug, locale)
                locale_val = updates.get("locale", getattr(item, "locale", None))
                if locale_val and hasattr(Model, "locale"):
                    existing = await session.exec(
                        select(Model).where(
                            getattr(Model, slug_field) == new_slug,
                            Model.locale == locale_val,
                            Model.id != item_id,
                        )
                    )
                else:
                    existing = await session.exec(
                        select(Model).where(getattr(Model, slug_field) == new_slug)
                    )
                if existing.first():
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")

        for field, value in updates.items():
            setattr(item, field, value)
        if hasattr(item, "updated_at"):
            item.updated_at = utcnow_naive()

        session.add(item)
        await session.commit()
        await session.refresh(item)
        return APIResponse(data=ReadSchema.model_validate(item))

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(
        item_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        _user=Depends(require_admin),
    ):
        item = await session.get(Model, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        await session.delete(item)
        await session.commit()

    return router


# ── Build sub-routers ─────────────────────────────────────────────────────────
applications_router = make_crud_router(
    prefix="/applications", tag="applications",
    Model=Application, ReadSchema=ApplicationRead,
    CreateSchema=ApplicationCreate, UpdateSchema=ApplicationUpdate,
)

faqs_router = make_crud_router(
    prefix="/faqs", tag="faqs",
    Model=FAQItem, ReadSchema=FAQItemRead,
    CreateSchema=FAQItemCreate, UpdateSchema=FAQItemUpdate,
    slug_field=None,
)

comparisons_router = make_crud_router(
    prefix="/comparisons", tag="comparisons",
    Model=ComparisonTopic, ReadSchema=ComparisonTopicRead,
    CreateSchema=ComparisonTopicCreate, UpdateSchema=ComparisonTopicUpdate,
)

certifications_router = make_crud_router(
    prefix="/certifications", tag="certifications",
    Model=Certification, ReadSchema=CertificationRead,
    CreateSchema=CertificationCreate, UpdateSchema=CertificationUpdate,
    slug_field="slug",
)

capabilities_router = make_crud_router(
    prefix="/capabilities", tag="capabilities",
    Model=Capability, ReadSchema=CapabilityRead,
    CreateSchema=CapabilityCreate, UpdateSchema=CapabilityUpdate,
)

ctas_router = make_crud_router(
    prefix="/ctas", tag="ctas",
    Model=CTA, ReadSchema=CTARead,
    CreateSchema=CTACreate, UpdateSchema=CTAUpdate,
    slug_field="cta_key",
)

pages_router = make_crud_router(
    prefix="/pages", tag="pages",
    Model=Page, ReadSchema=PageRead,
    CreateSchema=PageCreate, UpdateSchema=PageUpdate,
)

briefs_router = make_crud_router(
    prefix="/briefs", tag="briefs",
    Model=PageBrief, ReadSchema=PageBriefRead,
    CreateSchema=PageBriefCreate, UpdateSchema=PageBriefUpdate,
    slug_field=None,
)
