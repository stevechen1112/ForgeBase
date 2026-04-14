"""
Orphan Entity Detection API  (1a.1.10)

Returns entities that have no M2M associations:
  GET /content/entities/orphans          → summary counts
  GET /content/entities/orphans/products → products with no applications, no faqs
  GET /content/entities/orphans/applications → applications with no products
  GET /content/entities/orphans/faqs     → faqs not linked to any product or application
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.db.session import get_session
from app.models.associations import (
    ProductApplicationLink,
    ProductCertificationLink,
    ProductFAQLink,
    ApplicationFAQLink,
)
from app.models.application import Application
from app.models.faq_item import FAQItem
from app.models.product import Product
from app.models.user import User

router = APIRouter(prefix="/entities", tags=["Orphan Entities"])


# ── Response schemas ──────────────────────────────────────────────────────────

class OrphanProductOut(BaseModel):
    id: uuid.UUID
    product_name: str
    slug: str
    status: str
    locale: str
    reason: str  # human-readable explanation


class OrphanApplicationOut(BaseModel):
    id: uuid.UUID
    application_name: str
    slug: str
    status: str
    locale: str
    reason: str


class OrphanFAQOut(BaseModel):
    id: uuid.UUID
    question: str
    category_tag: Optional[str]
    status: str
    locale: str
    reason: str


class OrphanSummary(BaseModel):
    orphan_products: int
    orphan_applications: int
    orphan_faqs: int


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _orphan_product_ids(session: AsyncSession, tenant_id: uuid.UUID | None) -> set[uuid.UUID]:
    """Products that have no application link AND no FAQ link."""
    # product_ids that have at least one application
    has_app = set(
        (await session.exec(select(ProductApplicationLink.product_id).distinct())).all()
    )
    # product_ids that have at least one faq
    has_faq = set(
        (await session.exec(select(ProductFAQLink.product_id).distinct())).all()
    )
    # all product ids
    product_query = select(Product.id)
    if tenant_id:
        product_query = product_query.where(Product.tenant_id == tenant_id)
    all_products = await session.exec(product_query)
    return {pid for pid in all_products.all() if pid not in has_app and pid not in has_faq}


async def _orphan_application_ids(session: AsyncSession, tenant_id: uuid.UUID | None) -> set[uuid.UUID]:
    """Applications that have no product link."""
    has_product = set(
        (await session.exec(select(ProductApplicationLink.application_id).distinct())).all()
    )
    app_query = select(Application.id)
    if tenant_id:
        app_query = app_query.where(Application.tenant_id == tenant_id)
    all_apps = await session.exec(app_query)
    return {aid for aid in all_apps.all() if aid not in has_product}


async def _orphan_faq_ids(session: AsyncSession, tenant_id: uuid.UUID | None) -> set[uuid.UUID]:
    """FAQs not linked to any product or application."""
    has_product = set(
        (await session.exec(select(ProductFAQLink.faq_item_id).distinct())).all()
    )
    has_app = set(
        (await session.exec(select(ApplicationFAQLink.faq_item_id).distinct())).all()
    )
    faq_query = select(FAQItem.id)
    if tenant_id:
        faq_query = faq_query.where(FAQItem.tenant_id == tenant_id)
    all_faqs = await session.exec(faq_query)
    return {fid for fid in all_faqs.all() if fid not in has_product and fid not in has_app}


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/orphans", response_model=OrphanSummary)
async def get_orphan_summary(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> OrphanSummary:
    """Return count summary of all orphaned entities."""
    orphan_p = await _orphan_product_ids(session, current_user.tenant_id)
    orphan_a = await _orphan_application_ids(session, current_user.tenant_id)
    orphan_f = await _orphan_faq_ids(session, current_user.tenant_id)
    return OrphanSummary(
        orphan_products=len(orphan_p),
        orphan_applications=len(orphan_a),
        orphan_faqs=len(orphan_f),
    )


@router.get("/orphans/products", response_model=list[OrphanProductOut])
async def get_orphan_products(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[OrphanProductOut]:
    """Return products with no application or FAQ links."""
    orphan_ids = await _orphan_product_ids(session, current_user.tenant_id)
    if not orphan_ids:
        return []
    products = await session.exec(
        select(Product).where(col(Product.id).in_(orphan_ids)).order_by(Product.product_name)
    )
    return [
        OrphanProductOut(
            id=p.id,
            product_name=p.product_name,
            slug=p.slug,
            status=p.status,
            locale=p.locale,
            reason="No linked applications or FAQs",
        )
        for p in products.all()
    ]


@router.get("/orphans/applications", response_model=list[OrphanApplicationOut])
async def get_orphan_applications(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[OrphanApplicationOut]:
    """Return applications with no product links."""
    orphan_ids = await _orphan_application_ids(session, current_user.tenant_id)
    if not orphan_ids:
        return []
    apps = await session.exec(
        select(Application).where(col(Application.id).in_(orphan_ids)).order_by(Application.application_name)
    )
    return [
        OrphanApplicationOut(
            id=a.id,
            application_name=a.application_name,
            slug=a.slug,
            status=a.status,
            locale=a.locale,
            reason="No linked products",
        )
        for a in apps.all()
    ]


@router.get("/orphans/faqs", response_model=list[OrphanFAQOut])
async def get_orphan_faqs(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[OrphanFAQOut]:
    """Return FAQs not linked to any product or application."""
    orphan_ids = await _orphan_faq_ids(session, current_user.tenant_id)
    if not orphan_ids:
        return []
    faqs = await session.exec(
        select(FAQItem).where(col(FAQItem.id).in_(orphan_ids)).order_by(FAQItem.question)
    )
    return [
        OrphanFAQOut(
            id=f.id,
            question=f.question,
            category_tag=f.category_tag,
            status=f.status,
            locale=f.locale,
            reason="Not linked to any product or application",
        )
        for f in faqs.all()
    ]
