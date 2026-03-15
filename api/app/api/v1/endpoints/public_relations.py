"""
Public (no-auth) M2M relation read endpoints  (1a.5.12)

Used by the public-facing web frontend to show:
  - Products linked to an application (reverse lookup)
  - Applications linked to a product
  - Certifications linked to a product
  - FAQs linked to a product or application

All returned data uses the public-facing schemas from the respective models.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_session
from sqlalchemy import or_
from app.models.associations import (
    ProductApplicationLink,
    ProductCertificationLink,
    ProductFAQLink,
    ApplicationFAQLink,
    AlternativePartLink,
)
from app.models.application import Application
from app.models.certification import Certification
from app.models.faq_item import FAQItem
from app.models.product import Product
from app.models.product_category import ProductCategory

router = APIRouter(tags=["Public Relations"])


# ── Lightweight public schemas ────────────────────────────────────────────────

class PublicRelatedApplication(BaseModel):
    id: uuid.UUID
    application_name: str
    slug: str
    industry: str | None = None
    description: str | None = None


class PublicRelatedProduct(BaseModel):
    id: uuid.UUID
    product_name: str
    slug: str
    category_slug: str | None = None
    model_number: str | None = None
    short_description: str | None = None


class PublicRelatedCertification(BaseModel):
    id: uuid.UUID
    cert_name: str
    issuing_body: str | None = None
    description: str | None = None
    badge_icon_url: str | None = None


class PublicRelatedFAQ(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    locale: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# Product → Applications (forward)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/public/products/{product_id}/applications",
    response_model=list[PublicRelatedApplication],
)
async def public_list_product_applications(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await session.refresh(product, ["applications"])
    return [
        PublicRelatedApplication(
            id=a.id,
            application_name=a.application_name,
            slug=a.slug,
            industry=a.industry,
            description=a.description,
        )
        for a in product.applications
        if a.status == "published"
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Application → Products (reverse lookup)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/public/applications/{application_id}/products",
    response_model=list[PublicRelatedProduct],
)
async def public_list_application_products(
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    app = await session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Reverse lookup via ProductApplicationLink
    rows = (
        await session.exec(
            select(ProductApplicationLink).where(
                ProductApplicationLink.application_id == application_id
            )
        )
    ).all()

    product_ids = [r.product_id for r in rows]
    if not product_ids:
        return []

    products = (
        await session.exec(
            select(Product, ProductCategory.slug)
            .join(ProductCategory, Product.category_id == ProductCategory.id)
            .where(
                Product.id.in_(product_ids),
                Product.status == "published",
            )
        )
    ).all()

    return [
        PublicRelatedProduct(
            id=p.id,
            product_name=p.product_name,
            slug=p.slug,
            category_slug=category_slug,
            model_number=p.model_number,
            short_description=p.short_description,
        )
        for p, category_slug in products
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Product → Certifications
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/public/products/{product_id}/certifications",
    response_model=list[PublicRelatedCertification],
)
async def public_list_product_certifications(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await session.refresh(product, ["certifications"])
    return [
        PublicRelatedCertification(
            id=c.id,
            cert_name=c.cert_name,
            issuing_body=c.issuer,
            description=c.description,
            badge_icon_url=c.badge_image_url,
        )
        for c in product.certifications
        if c.status == "published"
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Product → FAQs
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/public/products/{product_id}/faqs",
    response_model=list[PublicRelatedFAQ],
)
async def public_list_product_faqs(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await session.refresh(product, ["faqs"])
    return [
        PublicRelatedFAQ(
            id=f.id,
            question=f.question,
            answer=f.answer,
            locale=f.locale,
        )
        for f in product.faqs
        if f.status == "published"
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Product → Alternatives (2.3.3 bidirectional)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/public/products/{product_id}/alternatives",
    response_model=list[PublicRelatedProduct],
)
async def public_list_product_alternatives(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    rows = (
        await session.exec(
            select(AlternativePartLink).where(
                or_(
                    AlternativePartLink.product_id == product_id,
                    AlternativePartLink.alternative_product_id == product_id,
                )
            )
        )
    ).all()

    partner_ids = [
        r.alternative_product_id if r.product_id == product_id else r.product_id
        for r in rows
    ]
    if not partner_ids:
        return []

    products = (
        await session.exec(
            select(Product, ProductCategory.slug)
            .join(ProductCategory, Product.category_id == ProductCategory.id)
            .where(
                Product.id.in_(partner_ids),
                Product.status == "published",
            )
        )
    ).all()

    return [
        PublicRelatedProduct(
            id=p.id,
            product_name=p.product_name,
            slug=p.slug,
            category_slug=category_slug,
            model_number=p.model_number,
            short_description=p.short_description,
        )
        for p, category_slug in products
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Application → FAQs
# ═══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/public/applications/{application_id}/faqs",
    response_model=list[PublicRelatedFAQ],
)
async def public_list_application_faqs(
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
):
    app = await session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    await session.refresh(app, ["faqs"])
    return [
        PublicRelatedFAQ(
            id=f.id,
            question=f.question,
            answer=f.answer,
            locale=f.locale,
        )
        for f in app.faqs
        if f.status == "published"
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-locale locale list (2.2.1) — for hreflang generation
# ═══════════════════════════════════════════════════════════════════════════════

class LocaleVariant(BaseModel):
    id: uuid.UUID
    locale: str
    product_name: str | None = None
    application_name: str | None = None


@router.get(
    "/public/products/{slug}/locales",
    response_model=list[LocaleVariant],
    summary="All locale versions of a product slug",
)
async def public_product_locales(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Returns every published locale variant that shares the same slug."""
    results = (
        await session.exec(
            select(Product).where(Product.slug == slug, Product.status == "published")
        )
    ).all()
    return [
        LocaleVariant(id=p.id, locale=p.locale, product_name=p.product_name)
        for p in results
    ]


@router.get(
    "/public/applications/{slug}/locales",
    response_model=list[LocaleVariant],
    summary="All locale versions of an application slug",
)
async def public_application_locales(
    slug: str,
    session: AsyncSession = Depends(get_session),
):
    """Returns every published locale variant that shares the same slug."""
    results = (
        await session.exec(
            select(Application).where(
                Application.slug == slug, Application.status == "published"
            )
        )
    ).all()
    return [
        LocaleVariant(id=a.id, locale=a.locale, application_name=a.application_name)
        for a in results
    ]
