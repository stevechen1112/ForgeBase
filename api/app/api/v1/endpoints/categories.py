"""
ProductCategory CRUD endpoint
GET    /api/v1/content/categories          — list (paginated)
POST   /api/v1/content/categories          — create (admin/marketing_manager)
GET    /api/v1/content/categories/tree      — full tree structure
GET    /api/v1/content/categories/{id}      — get one
PATCH  /api/v1/content/categories/{id}      — update (admin/marketing_manager)
DELETE /api/v1/content/categories/{id}      — delete (admin only)
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.models.product_category import ProductCategory
from app.models.user import User
from app.schemas.base import APIResponse, PaginationMeta
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryRead,
    ProductCategoryTree,
    ProductCategoryUpdate,
)
from app.services.knowledge_sync import sync_knowledge_now

router = APIRouter(prefix="/categories", tags=["categories"])


# ── helper ───────────────────────────────────────────────────────────────────
def _build_tree(cats: List[ProductCategory]) -> List[ProductCategoryTree]:
    lookup: dict[uuid.UUID, ProductCategoryTree] = {
        c.id: ProductCategoryTree.model_validate(c) for c in cats
    }
    roots: List[ProductCategoryTree] = []
    for node in lookup.values():
        if node.parent_id is None:
            roots.append(node)
        elif node.parent_id in lookup:
            lookup[node.parent_id].children.append(node)
    return roots


# ── endpoints ─────────────────────────────────────────────────────────────────
@router.get("", response_model=APIResponse)
async def list_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    slug: str | None = Query(None),
    locale: str = Query("en"),
    pair_status: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
    auth_user=Depends(optional_current_user),
):
    # 帶有效憑證時以 caller tenant 為準（與 content_crud 同規則），
    # 否則 admin 未送 X-Tenant-ID 時會落到 tenant IS NULL 而看不到資料
    if auth_user is not None and getattr(auth_user, "tenant_id", None):
        tenant_id = auth_user.tenant_id
    # locale="all" 不過濾（admin 查詢語言變體用）；預設 "en" 維持公開站行為
    base_q = select(ProductCategory)
    if locale != "all":
        from app.core.locale import to_content_locale
        normalized_locale = to_content_locale(locale, default="")
        if not normalized_locale:
            return APIResponse(
                data=[],
                meta=PaginationMeta(total=0, page=page, page_size=page_size, total_pages=0),
            )
        base_q = base_q.where(ProductCategory.locale == normalized_locale)
    if tenant_id:
        base_q = base_q.where(ProductCategory.tenant_id == tenant_id)
    else:
        base_q = base_q.where(ProductCategory.tenant_id.is_(None))
    if status:
        base_q = base_q.where(ProductCategory.status == status)
    if slug:
        base_q = base_q.where(ProductCategory.slug == slug)
    if pair_status:
        from app.services.locale_support import (
            apply_pair_status_filter,
            default_buyer_locale,
            get_source_locale,
        )
        source_locale = await get_source_locale(session, tenant_id)
        base_q = apply_pair_status_filter(
            base_q,
            ProductCategory,
            tenant_id=tenant_id,
            source_locale=source_locale,
            target_locale=default_buyer_locale(source_locale),
            pair_status=pair_status,
            key_field="slug",
        )

    total = await session.exec(select(func.count()).select_from(base_q.subquery()))
    total_count = total.one()

    items_q = base_q.order_by(ProductCategory.sort_order, ProductCategory.category_name)
    items_q = items_q.offset((page - 1) * page_size).limit(page_size)
    items = (await session.exec(items_q)).all()

    return APIResponse(
        data=[ProductCategoryRead.model_validate(c) for c in items],
        meta=PaginationMeta(
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=(total_count + page_size - 1) // page_size,
        ),
    )


@router.get("/tree", response_model=APIResponse)
async def get_category_tree(
    locale: str = Query("en"),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
):
    from app.core.locale import to_content_locale
    content_locale = to_content_locale(locale)
    q = (
        select(ProductCategory)
        .where(ProductCategory.locale == content_locale, ProductCategory.status == "published")
        .order_by(ProductCategory.sort_order)
    )
    if tenant_id:
        q = q.where(ProductCategory.tenant_id == tenant_id)
    else:
        q = q.where(ProductCategory.tenant_id.is_(None))
    cats = (await session.exec(q)).all()
    return APIResponse(data=_build_tree(list(cats)))


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: ProductCategoryCreate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_content_editor),
):
    from app.core.locale import to_content_locale

    locale = to_content_locale(payload.locale)
    existing = await session.exec(
        select(ProductCategory).where(
            ProductCategory.slug == payload.slug,
            ProductCategory.locale == locale,
            ProductCategory.tenant_id == _user.tenant_id,
        )
    )
    if existing.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug already exists")

    data = payload.model_dump()
    data["locale"] = locale
    cat = ProductCategory(**data)
    cat.tenant_id = _user.tenant_id
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    await sync_knowledge_now(session, tenant_id=_user.tenant_id, item=cat)
    await session.commit()
    return APIResponse(data=ProductCategoryRead.model_validate(cat))


@router.get("/{category_id}", response_model=APIResponse)
async def get_category(
    category_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
    auth_user=Depends(optional_current_user),
):
    # 帶有效憑證時以 caller tenant 為準（與 list 同規則）
    if auth_user is not None and getattr(auth_user, "tenant_id", None):
        tenant_id = auth_user.tenant_id
    cat = await session.get(ProductCategory, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    if cat.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    return APIResponse(data=ProductCategoryRead.model_validate(cat))


@router.patch("/{category_id}", response_model=APIResponse)
async def update_category(
    category_id: uuid.UUID,
    payload: ProductCategoryUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_content_editor),
):
    from app.core.locale import to_content_locale

    cat = await session.get(ProductCategory, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    if not _user.is_superuser and cat.tenant_id != _user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")

    updates = payload.model_dump(exclude_unset=True)
    if "locale" in updates and updates["locale"] is not None:
        updates["locale"] = to_content_locale(str(updates["locale"]))

    # Check slug uniqueness if slug is being changed
    if "slug" in updates and updates["slug"] != cat.slug:
        existing = await session.exec(
            select(ProductCategory).where(
                ProductCategory.slug == updates["slug"],
                ProductCategory.locale == updates.get("locale", cat.locale),
                ProductCategory.tenant_id == _user.tenant_id,
                ProductCategory.id != category_id,
            )
        )
        if existing.first():
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug already exists")

    for field, value in updates.items():
        setattr(cat, field, value)
    cat.updated_at = utcnow_naive()

    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    await sync_knowledge_now(session, tenant_id=_user.tenant_id, item=cat)
    await session.commit()
    return APIResponse(data=ProductCategoryRead.model_validate(cat))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
):
    cat = await session.get(ProductCategory, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    if not _user.is_superuser and cat.tenant_id != _user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Category not found")
    await sync_knowledge_now(session, tenant_id=_user.tenant_id, item=cat, action="tombstone")
    await session.delete(cat)
    await session.commit()
