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
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from slugify import slugify
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import (
    optional_current_user,
    require_admin,
    require_content_editor,
    resolve_tenant_id,
)
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.comparison_topic import ComparisonTopic
from app.models.cta import CTA
from app.models.faq_item import FAQItem
from app.models.idempotency_key import IdempotencyKey
from app.models.page import Page
from app.schemas.base import APIResponse, PaginationMeta
from app.schemas.content import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationUpdate,
    CapabilityCreate,
    CapabilityRead,
    CapabilityUpdate,
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    ComparisonTopicCreate,
    ComparisonTopicRead,
    ComparisonTopicUpdate,
    CTACreate,
    CTARead,
    CTAUpdate,
    FAQItemCreate,
    FAQItemRead,
    FAQItemUpdate,
    PageCreate,
    PageRead,
    PageUpdate,
)
from app.services.html_sanitize import sanitize_html
from app.services.knowledge_sync import source_type_for, sync_knowledge_now
from app.services.revalidate import revalidate_page

logger = logging.getLogger(__name__)


async def _sync_public_index(session: AsyncSession, item: Any, *, action: str = "compile") -> None:
    if source_type_for(item) is None:
        return
    tenant_id = getattr(item, "tenant_id", None)
    try:
        await sync_knowledge_now(session, tenant_id=tenant_id, item=item, action=action)
        await session.commit()
    except Exception:
        logger.exception("public knowledge sync failed")


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


def normalize_datetimes(values: dict[str, Any]) -> dict[str, Any]:
    """Store API timezone-aware datetimes in the legacy UTC-naive columns."""
    for key, value in values.items():
        if isinstance(value, datetime) and value.tzinfo is not None:
            values[key] = value.astimezone(timezone.utc).replace(tzinfo=None)
    return values


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
    mutation_guard=require_content_editor,
    create_guard=require_content_editor,
    editor_update_fields: tuple[str, ...] | None = None,
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

    def _apply_public_tenant_scope(
        query,
        tenant_id: uuid.UUID | None,
    ):
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
        if item_tenant_id != tenant_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

    def _editor_can_mutate(item: Any, user: Any) -> bool:
        if getattr(user, "is_superuser", False):
            return True
        if not hasattr(item, "tenant_id"):
            return True
        item_tenant_id = getattr(item, "tenant_id", None)
        if item_tenant_id is None:
            return False
        return item_tenant_id == getattr(user, "tenant_id", None)

    @router.get("", response_model=APIResponse)
    async def list_items(
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
        item_status: str | None = Query(None, alias="status"),
        locale: str | None = Query(None),
        slug: str | None = Query(None),
        page_type: str | None = Query(None),
        pair_status: str | None = Query(None),
        variant_key: str | None = Query(None),
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
            from app.core.locale import to_content_locale
            normalized_locale = to_content_locale(locale, default="")
            if not normalized_locale:
                return APIResponse(
                    data=[],
                    meta=PaginationMeta(total=0, page=page, page_size=page_size, total_pages=0),
                )
            base_q = base_q.where(Model.locale == normalized_locale)
        if pair_status and hasattr(Model, "locale"):
            from app.services.locale_support import (
                apply_pair_status_filter,
                default_buyer_locale,
                get_source_locale,
            )
            source_locale = await get_source_locale(session, tenant_id)
            key = slug_field or ("variant_key" if hasattr(Model, "variant_key") else "slug")
            if key and hasattr(Model, key):
                base_q = apply_pair_status_filter(
                    base_q,
                    Model,
                    tenant_id=tenant_id,
                    source_locale=source_locale,
                    target_locale=default_buyer_locale(source_locale),
                    pair_status=pair_status,
                    key_field=key,
                )
        if item_status and hasattr(Model, "status"):
            base_q = base_q.where(Model.status == item_status)
        if auth_user is None and Model is Certification:
            # Keep expired records available to editors for audit/history, but
            # never advertise them on public trust and certification surfaces.
            base_q = base_q.where(
                or_(Certification.expires_at.is_(None), Certification.expires_at >= utcnow_naive())
            )
        if slug and hasattr(Model, "slug"):
            base_q = base_q.where(Model.slug == slug)
        if variant_key and hasattr(Model, "variant_key"):
            base_q = base_q.where(Model.variant_key == variant_key)
        if page_type and hasattr(Model, "page_type"):
            base_q = base_q.where(Model.page_type == page_type)

        total = (await session.exec(select(func.count()).select_from(base_q.subquery()))).one()
        order_col = getattr(Model, "sort_order", None) or Model.created_at
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
        _user=Depends(create_guard),
    ):
        tenant_id = _user.tenant_id if hasattr(Model, "tenant_id") else None

        # Idempotency-Key（CF→FB 契約 §6）：重送時回傳首次結果
        idem_key = request.headers.get("Idempotency-Key")
        endpoint_id = f"POST {prefix}"
        if idem_key:
            # Serialize the first write for this key before checking either the
            # idempotency ledger or the resource slug.  Without this lock, a
            # concurrent loser can miss the uncommitted ledger row and then
            # observe the winner's committed slug, incorrectly returning 409.
            if session.get_bind().dialect.name == "postgresql":
                await session.exec(
                    text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
                    params={"lock_key": f"forgebase-idem:{tenant_id}:{endpoint_id}:{idem_key}"},
                )
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
                if locale_val and hasattr(Model, "locale"):
                    from app.core.locale import to_content_locale
                    locale_val = to_content_locale(str(locale_val))
                    conflict_q_locale = locale_val
                else:
                    conflict_q_locale = None
                conflict_q = select(Model).where(getattr(Model, slug_field) == slug_val)
                if conflict_q_locale and hasattr(Model, "locale"):
                    conflict_q = conflict_q.where(Model.locale == conflict_q_locale)
                if hasattr(Model, "tenant_id"):
                    conflict_q = conflict_q.where(Model.tenant_id == tenant_id)
                existing = await session.exec(conflict_q)
                if existing.first():
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")

        dump = normalize_datetimes(payload.model_dump())
        if slug_field and generated_slug:
            dump[slug_field] = generated_slug
        # inject created_by and tenant_id for models that support them
        if hasattr(Model, "created_by") and _user:
            dump["created_by"] = _user.id
        if hasattr(Model, "tenant_id") and _user and _user.tenant_id:
            dump.setdefault("tenant_id", _user.tenant_id)
        if "locale" in dump and dump["locale"] is not None:
            from app.core.locale import to_content_locale
            dump["locale"] = to_content_locale(str(dump["locale"]))
        # FAQ: ensure variant_key for manually maintained locale variants.
        if Model is FAQItem and not dump.get("variant_key"):
            import uuid as _uuid
            dump["variant_key"] = f"faq-{_uuid.uuid4().hex[:16]}"
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
                    from app.core.locale import to_content_locale
                    conflict_q = conflict_q.where(Model.locale == to_content_locale(str(locale_val)))
                if hasattr(Model, "tenant_id"):
                    conflict_q = conflict_q.where(Model.tenant_id == tenant_id)
                existing = (await session.exec(conflict_q)).first()
                if existing:
                    raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{slug_field} already exists")
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Conflict creating resource")
        await session.refresh(item)
        await _sync_public_index(session, item)
        return APIResponse(data=ReadSchema.model_validate(item))

    @router.get("/{item_id}", response_model=APIResponse)
    async def get_item(
        item_id: uuid.UUID,
        session: AsyncSession = Depends(get_session),
        tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
        auth_user=Depends(optional_current_user),
    ):
        if auth_user is not None and getattr(auth_user, "tenant_id", None):
            tenant_id = auth_user.tenant_id
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
        _user=Depends(mutation_guard),
    ):
        item = await session.get(Model, item_id)
        if not item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        if not _editor_can_mutate(item, _user):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")

        updates = normalize_datetimes(payload.model_dump(exclude_unset=True))
        if (
            editor_update_fields is not None
            and _user.role == "marketing_manager"
            and any(key not in editor_update_fields for key in updates)
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="This role may only update approved page content fields",
            )
        if "locale" in updates and updates["locale"] is not None:
            from app.core.locale import to_content_locale
            updates["locale"] = to_content_locale(str(updates["locale"]))

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
        await _sync_public_index(session, item)
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
        if not _editor_can_mutate(item, _user):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Not found")
        await _sync_public_index(session, item, action="tombstone")
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
    mutation_guard=require_content_editor,
    create_guard=require_admin,
    editor_update_fields=("title", "subtitle", "body", "hero_image_url"),
)
