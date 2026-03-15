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

from app.api.v1.deps import get_current_user, require_admin, require_content_editor
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.product import Product
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
):
    base_q = select(Product)
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
            Product.product_name.ilike(term) | Product.model_number.ilike(term)  # type: ignore[attr-defined]
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
):
    # slug uniqueness is per-locale; model_number is globally unique
    slug_conflict = await session.exec(
        select(Product).where(Product.slug == payload.slug, Product.locale == payload.locale)
    )
    if slug_conflict.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="slug already exists for this locale")
    mn_conflict = await session.exec(
        select(Product).where(Product.model_number == payload.model_number)
    )
    if mn_conflict.first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="model_number already exists")

    product = Product(**payload.model_dump())
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return APIResponse(data=ProductRead.model_validate(product))


@router.get("/{product_id}", response_model=APIResponse)
async def get_product(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    return APIResponse(data=ProductRead.model_validate(product))


@router.patch("/{product_id}", response_model=APIResponse)
async def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    session: AsyncSession = Depends(get_session),
    _user=Depends(require_content_editor),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")

    updates = payload.model_dump(exclude_unset=True)
    if "slug" in updates and updates["slug"] != product.slug:
        locale_to_check = updates.get("locale", product.locale)
        slug_conflict = await session.exec(
            select(Product).where(
                Product.slug == updates["slug"],
                Product.locale == locale_to_check,
                Product.id != product_id,
            )
        )
        if slug_conflict.first():
            raise HTTPException(status.HTTP_409_CONFLICT, detail="slug already exists for this locale")
    if "model_number" in updates and updates["model_number"] != product.model_number:
        mn_conflict = await session.exec(
            select(Product).where(Product.model_number == updates["model_number"])
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
    _user=Depends(require_admin),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Product not found")
    await session.delete(product)
    await session.commit()
