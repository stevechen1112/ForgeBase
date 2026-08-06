"""
Remaining content CRUD endpoints:
  /api/v1/content/applications
  /api/v1/content/faqs
  /api/v1/content/comparisons
  /api/v1/content/certifications
  /api/v1/content/capabilities
  /api/v1/content/ctas
  /api/v1/content/pages
"""
import asyncio
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlmodel import select, func, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from slugify import slugify

from app.api.v1.deps import (
    get_current_user,
    optional_current_user,
    require_admin,
    require_content_editor,
    resolve_tenant_id,
)
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.application import Application
from app.models.faq_item import FAQItem
from app.models.comparison_topic import ComparisonTopic
from app.models.certification import Certification
from app.models.capability import Capability
from app.models.cta import CTA
from app.models.idempotency_key import IdempotencyKey
from app.models.page import Page
from app.schemas.base import APIResponse, PaginationMeta
from app.services.html_sanitize import sanitize_html
from app.services.revalidate import revalidate_page
from app.schemas.content import (
    ApplicationCreate, ApplicationRead, ApplicationUpdate,
    FAQItemCreate, FAQItemRead, FAQItemUpdate,
    ComparisonTopicCreate, ComparisonTopicRead, ComparisonTopicUpdate,
    CertificationCreate, CertificationRead, CertificationUpdate,
    CapabilityCreate, CapabilityRead, CapabilityUpdate,
    CTACreate, CTARead, CTAUpdate,
    PageCreate, PageRead, PageUpdate,
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
    sanitize_fields: tuple[str, ...] = (),
    revalidate_on_change: bool = False,
) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    def _sanitize_dump(dump: dict) -> dict:
        for field in sanitize_fields:
            if isinstance(dump.get(field), str):
                dump[field] = sanitize_html(dump[field])
        return dump

    def _schedule_revalidate(item: Any) -> None:
        if not revalidate_on_change:
            return
        slug = getattr(item, "slug", None)
        if not slug:
            return
        locale = getattr(item, "locale", "en") or "en"
        task = asyncio.create_task(revalidate_page(slug, locale, include_sitemap=True))
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

    def _apply_public_tenant_scope(query, tenant_id: uuid.UUID | None):
        tenant_col = getattr(Model, "tenant_id", None)
        if tenant_col is None:
            return query
        if tenant_id is None:
            return query.where(tenant_col.is_(None))
        return query.where(tenant_col == tenant_id)

    def _ensure_item_access(item: Any, tenant_id: uuid.UUID | None) -> None:
        if not hasattr(item, "tenant_id"):
            return
        item_tenant_id = getattr(item, "tenant_id", None)
        if tenant_id is None:
            if item_tenant_id is not None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
            return
        if item_tenant_id != tenant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    @router.get("", response_model=APIResponse)
    async def list_items(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        item_status: str | None = Query(None, alias="status"),
        locale: str | None = Query(None),
        slug: str | None = Query(None),
        page_type: str | None = Query(None),
        session: AsyncSession = Depends(get_session),
        tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
        auth_user=Depends(optional_current_user),
    ):
        # 帶有效憑證（如 CF service account）時以 caller tenant 為準，
        # 覆寫 host/header 解析（契約 §5.1 slug 查詢流程依賴此行為）
        if auth_user is not None and getattr(auth_user, "tenant_id", None):
            tenant_id = auth_user.tenant_id
        base_q = select(Model)
        base_q = _apply_public_tenant_scope(base_q, tenant_id)
        if locale_filter and hasattr(Model, "locale") and locale:
            base_q = base_q.where(Model.locale == locale)
        if item_status and hasattr(Model, "status"):
            base_q = base_q.where(Model.status == item_status)
        if slug and hasattr(Model, "slug"):
            base_q = base_q.where(Model.slug == slug)
        if page_type and hasattr(Model, "page_type"):
            base_q = base_q.where(Model.page_type == page_type)

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
        payload: CreateSchema,
        request: Request,
        session: AsyncSession = Depends(get_session),
        _user=Depends(require_content_editor),
    ):
        tenant_id = _user.tenant_id if hasattr(Model, "tenant_id") else None

        # Idempotency-Key（CF→FB 契約 §6）：重送時回傳首次結果
        idem_key = request.headers.get("Idempotency-Key")
        endpoint_id = f"POST {prefix}"
        if idem_key:
            idem_q = select(IdempotencyKey).where(
                IdempotencyKey.key == idem_key,
                IdempotencyKey.endpoint == endpoint_id,
                IdempotencyKey.tenant_id == tenant_id,
            )
            stored = (await session.exec(idem_q)).first()
            if stored:
                return JSONResponse(
                    status_code=stored.status_code,
                    content=json.loads(stored.response_json),
                )

        generated_slug = build_slug(payload, slug_field)
        if slug_field:
            slug_val = generated_slug
            if slug_val:
                # if model has locale, uniqueness is per (slug, locale)
                locale_val = getattr(payload, "locale", None)
                conflict_q = select(Model).where(getattr(Model, slug_field) == slug_val)
                if locale_val and hasattr(Model, "locale"):
                    conflict_q = conflict_q.where(Model.locale == locale_val)
                if hasattr(Model, "tenant_id"):
                    conflict_q = conflict_q.where(Model.tenant_id == tenant_id)
                existing = await session.exec(conflict_q)
                if existing.first():
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")

        dump = payload.model_dump()
        if slug_field and generated_slug:
            dump[slug_field] = generated_slug
        # inject created_by and tenant_id for models that support them
        if hasattr(Model, "created_by") and _user:
            dump["created_by"] = _user.id
        if hasattr(Model, "tenant_id") and _user and _user.tenant_id:
            dump.setdefault("tenant_id", _user.tenant_id)
        dump = _sanitize_dump(dump)

        # 頁面建立與 Idempotency-Key 寫入同一交易：
        # 併發同 key 時 loser 整筆 rollback，改回傳 winner 的首次結果（契約 §6）。
        # flush/commit 皆可能因 slug 或 key 唯一約束失敗，一併捕獲。
        try:
            item = Model(**dump)
            session.add(item)
            await session.flush()
            response = APIResponse(data=ReadSchema.model_validate(item))
            if idem_key:
                session.add(IdempotencyKey(
                    tenant_id=tenant_id,
                    endpoint=endpoint_id,
                    key=idem_key,
                    status_code=201,
                    response_json=response.model_dump_json(),
                ))
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if idem_key:
                stored = (await session.exec(
                    select(IdempotencyKey).where(
                        IdempotencyKey.key == idem_key,
                        IdempotencyKey.endpoint == endpoint_id,
                        IdempotencyKey.tenant_id == tenant_id,
                    )
                )).first()
                if stored:
                    return JSONResponse(
                        status_code=stored.status_code,
                        content=json.loads(stored.response_json),
                    )
            # slug 唯一約束競態（無 key 或 key 尚未寫入）
            if slug_field and generated_slug:
                locale_val = getattr(payload, "locale", None)
                conflict_q = select(Model).where(getattr(Model, slug_field) == generated_slug)
                if locale_val and hasattr(Model, "locale"):
                    conflict_q = conflict_q.where(Model.locale == locale_val)
                if hasattr(Model, "tenant_id"):
                    conflict_q = conflict_q.where(Model.tenant_id == tenant_id)
                existing = (await session.exec(conflict_q)).first()
                if existing:
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Conflict creating resource")
        await session.refresh(item)
        return APIResponse(data=ReadSchema.model_validate(item))

    @router.get("/{item_id}", response_model=APIResponse)
    async def get_item(
        item_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
    ):
        item = await session.get(Model, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        _ensure_item_access(item, tenant_id)
        return APIResponse(data=ReadSchema.model_validate(item))

    @router.patch("/{item_id}", response_model=APIResponse)
    async def update_item(
        item_id: uuid.UUID,
        payload: UpdateSchema,
        session: AsyncSession = Depends(get_session),
        _user=Depends(require_content_editor),
    ):
        item = await session.get(Model, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        if hasattr(item, "tenant_id") and getattr(item, "tenant_id", None) != _user.tenant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

        updates = payload.model_dump(exclude_unset=True)
        if slug_field and slug_field in updates:
            new_slug = updates[slug_field]
            if new_slug != getattr(item, slug_field):
                # if model has locale, uniqueness is per (slug, locale)
                locale_val = updates.get("locale", getattr(item, "locale", None))
                conflict_q = select(Model).where(
                    getattr(Model, slug_field) == new_slug,
                    Model.id != item_id,
                )
                if locale_val and hasattr(Model, "locale"):
                    conflict_q = conflict_q.where(Model.locale == locale_val)
                if hasattr(Model, "tenant_id"):
                    conflict_q = conflict_q.where(Model.tenant_id == _user.tenant_id)
                existing = await session.exec(conflict_q)
                if existing.first():
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")

        for field, value in updates.items():
            setattr(item, field, value)
        if hasattr(item, "updated_at"):
            item.updated_at = utcnow_naive()
        _sanitize_dump_item = {f: getattr(item, f) for f in sanitize_fields}
        for f, v in _sanitize_dump(_sanitize_dump_item).items():
            setattr(item, f, v)

        session.add(item)
        await session.commit()
        await session.refresh(item)
        if getattr(item, "status", None) == "published":
            _schedule_revalidate(item)
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
        if hasattr(item, "tenant_id") and getattr(item, "tenant_id", None) != _user.tenant_id:
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
    sanitize_fields=("body",),
    revalidate_on_change=True,
)
