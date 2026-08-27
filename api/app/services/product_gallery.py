"""Attach ordered product gallery images without N+1 queries."""
from __future__ import annotations

import uuid
from collections import defaultdict

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.content_asset import ContentAsset
from app.models.product import Product
from app.schemas.product import ProductGalleryImage, ProductRead


async def load_gallery_map(
    session: AsyncSession,
    product_ids: list[uuid.UUID],
    tenant_id: uuid.UUID | None,
) -> dict[uuid.UUID, list[ProductGalleryImage]]:
    if not product_ids:
        return {}
    statement = select(ContentAsset).where(
        ContentAsset.product_id.in_(product_ids),
        ContentAsset.asset_type == "image",
    )
    if tenant_id:
        statement = statement.where(ContentAsset.tenant_id == tenant_id)
    statement = statement.order_by(ContentAsset.display_order, ContentAsset.created_at)
    rows = (await session.exec(statement)).all()
    grouped: dict[uuid.UUID, list[ProductGalleryImage]] = defaultdict(list)
    for asset in rows:
        if not asset.product_id:
            continue
        grouped[asset.product_id].append(
            ProductGalleryImage(
                id=asset.id,
                public_url=asset.public_url,
                alt_text=asset.alt_text,
                display_order=asset.display_order,
            )
        )
    return grouped


def to_product_read(product: Product, gallery: list[ProductGalleryImage] | None = None) -> ProductRead:
    payload = ProductRead.model_validate(product)
    return payload.model_copy(update={"gallery_images": gallery or []})


async def products_to_read(
    session: AsyncSession,
    products: list[Product],
    tenant_id: uuid.UUID | None,
) -> list[ProductRead]:
    gallery_map = await load_gallery_map(session, [item.id for item in products], tenant_id)
    return [to_product_read(item, gallery_map.get(item.id, [])) for item in products]
