"""
Product CRUD endpoint
GET    /api/v1/content/products
POST   /api/v1/content/products
GET    /api/v1/content/products/{id}
PATCH  /api/v1/content/products/{id}
DELETE /api/v1/content/products/{id}
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_admin, require_content_editor, QuotaEnforcer, resolve_tenant_id, optional_current_user
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.product import Product
from app.models.user import User
from app.schemas.base import APIResponse, PaginationMeta
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=APIResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    category_id: uuid.UUID | None = Query(None),
    locale: str | None = Query(None),
    slug: str | None = Query(None),
    q: str | None = Query(None, description="Full-text search on product_name and model_number"),
    featured: bool | None = Query(None, description="Filter by is_featured"),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
    auth_user=Depends(optional_current_user),
):
    # 帶有效憑證時以 caller tenant 為準（與 content_crud 同規則），
    # 否則 admin 未送 X-Tenant-ID 時會落到 tenant IS NULL 而看不到資料
    if auth_user is not None and getattr(auth_user, "tenant_id", None):
        tenant_id = auth_user.tenant_id
    base_q = select(Product)
    if tenant_id:
        # Authenticated tenant editors also see legacy NULL-tenant rows.
        if auth_user is not None and getattr(auth_user, "tenant_id", None):
            base_q = base_q.where(
                (Product.tenant_id == tenant_id) | (Product.tenant_id.is_(None))
            )
        else:
            base_q = base_q.where(Product.tenant_id == tenant_id)
    else:
        base_q = base_q.where(Product.tenant_id.is_(None))
    if locale:
        base_q = base_q.where(Product.locale == locale)
    if status:
        base_q = base_q.where(Product.status == status)
    if category_id:
        base_q = base_q.where(Product.category_id == category_id)
    if slug:
        base_q = base_q.where(Product.slug == slug)
    if q:
        term = f"%{q}%"
        base_q = base_q.where(
            Product.product_name.ilike(term) | Product.model_number.ilike(term)
        )
    if featured is not None:
        base_q = base_q.where(Product.is_featured == featured)

    total = (await session.exec(select(func.count()).select_from(base_q.subquery()))).one()
    items_q = base_q.order_by(Product.display_priority.desc(), Product.product_name).offset((page - 1) * page_size).limit(page_size)
    items = (await session.exec(items_q)).all()

    return APIResponse(
        data=[ProductRead.model_validate(p) for p in items],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        ),
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_content_editor),
    _quota=Depends(QuotaEnforcer("product")),
):
    # slug uniqueness is per tenant+locale; model_number is per tenant
    slug_conflict = await session.exec(
        select(Product).where(
            Product.slug == payload.slug,
            Product.locale == payload.locale,
            Product.tenant_id == _user.tenant_id,
        )
    )
    if slug_conflict.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="slug already exists for this locale")
    mn_conflict = await session.exec(
        select(Product).where(
            Product.model_number == payload.model_number,
            Product.tenant_id == _user.tenant_id,
        )
    )
    if mn_conflict.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="model_number already exists")

    product = Product(**payload.model_dump())
    product.tenant_id = _user.tenant_id
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return APIResponse(data=ProductRead.model_validate(product))


@router.get("/{product_id}", response_model=APIResponse)
async def get_product(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
    auth_user=Depends(optional_current_user),
):
    # 帶有效憑證時以 caller tenant 為準（與 list 同規則）
    if auth_user is not None and getattr(auth_user, "tenant_id", None):
        tenant_id = auth_user.tenant_id
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    if tenant_id is None and product.tenant_id is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    if tenant_id is not None and product.tenant_id is not None and product.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return APIResponse(data=ProductRead.model_validate(product))


@router.patch("/{product_id}", response_model=APIResponse)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_content_editor),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    if _user.tenant_id and product.tenant_id is not None and product.tenant_id != _user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    if "slug" in updates and updates["slug"] != product.slug:
        locale_to_check = updates.get("locale", product.locale)
        slug_conflict = await session.exec(
            select(Product).where(
                Product.slug == updates["slug"],
                Product.locale == locale_to_check,
                Product.id != product_id,
                Product.tenant_id == _user.tenant_id,
            )
        )
        if slug_conflict.first():
            raise HTTPException(status.HTTP_409_CONFLICT, detail="slug already exists for this locale")
    if "model_number" in updates and updates["model_number"] != product.model_number:
        mn_conflict = await session.exec(
            select(Product).where(
                Product.model_number == updates["model_number"],
                Product.tenant_id == _user.tenant_id,
            )
        )
        if mn_conflict.first():
            raise HTTPException(status.HTTP_409_CONFLICT, detail="model_number already exists")

    for field, value in updates.items():
        setattr(product, field, value)
    product.updated_at = utcnow_naive()

    session.add(product)
    await session.commit()
    await session.refresh(product)
    return APIResponse(data=ProductRead.model_validate(product))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(require_admin),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    if _user.tenant_id and product.tenant_id is not None and product.tenant_id != _user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    await session.delete(product)
    await session.commit()
