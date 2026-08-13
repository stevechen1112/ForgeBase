"""
M2M Entity Relationship Management API  (1a.1.9)

Manages many-to-many links between products and:
  - applications    GET/POST/DELETE /content/products/{id}/applications[/{app_id}]
  - certifications  GET/POST/DELETE /content/products/{id}/certifications[/{cert_id}]
  - faqs            GET/POST/DELETE /content/products/{id}/faqs[/{faq_id}]
  - alternatives    GET/POST/DELETE /content/products/{id}/alternatives[/{alt_id}]

Also application ↔ faqs:
  GET/POST/DELETE /content/applications/{id}/faqs[/{faq_id}]

Also application ↔ related-applications (self M2M):
  GET/POST/DELETE /content/applications/{id}/related-applications[/{related_id}]
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user, require_content_editor
from app.db.session import get_session
from app.models.associations import (
    ProductApplicationLink,
    ProductCertificationLink,
    ProductFAQLink,
    ApplicationFAQLink,
    AlternativePartLink,
    ApplicationRelatedLink,
)
from app.models.application import Application
from app.models.certification import Certification
from app.models.faq_item import FAQItem
from app.models.product import Product
from app.models.user import User


router = APIRouter(tags=["Entity Relations"])


def _tenant_visible(entity, tenant_id: uuid.UUID | None) -> bool:
    """Match content CRUD visibility, including editable legacy NULL-tenant rows."""
    entity_tenant_id = getattr(entity, "tenant_id", None)
    if tenant_id is None:
        return entity_tenant_id is None
    return entity_tenant_id is None or entity_tenant_id == tenant_id


def _ensure_tenant_match(entity, tenant_id: uuid.UUID | None, detail: str = "Not found"):
    if not _tenant_visible(entity, tenant_id):
        raise HTTPException(status_code=404, detail=detail)


# ── Small read schemas ────────────────────────────────────────────────────────

class RelatedItemOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


def _app_out(a: Application) -> RelatedItemOut:
    return RelatedItemOut(id=a.id, name=a.application_name, slug=a.slug)


def _cert_out(c: Certification) -> RelatedItemOut:
    return RelatedItemOut(id=c.id, name=c.cert_name, slug=c.cert_name.lower().replace(" ", "-"))


def _faq_out(f: FAQItem) -> RelatedItemOut:
    return RelatedItemOut(id=f.id, name=f.question[:80], slug=str(f.id))


# ── Helper: get product or 404 ────────────────────────────────────────────────

async def _get_product(product_id: uuid.UUID, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> Product:
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    _ensure_tenant_match(product, tenant_id, "Product not found")
    return product


# ═══════════════════════════════════════════════════════════════════════════════
# Product ↔ Applications
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/products/{product_id}/applications", response_model=list[RelatedItemOut])
async def list_product_applications(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product(product_id, session, current_user.tenant_id)
    await session.refresh(product, ["applications"])
    return [_app_out(a) for a in product.applications if _tenant_visible(a, current_user.tenant_id)]


@router.post("/products/{product_id}/applications/{application_id}",
             status_code=status.HTTP_201_CREATED)
async def link_product_application(
    product_id: uuid.UUID,
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    application = await session.get(Application, application_id)
    if not application or not _tenant_visible(application, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Application not found")

    existing = (await session.exec(
        select(ProductApplicationLink).where(
            ProductApplicationLink.product_id == product_id,
            ProductApplicationLink.application_id == application_id,
        )
    )).first()
    if existing:
        return {"detail": "Already linked"}

    session.add(ProductApplicationLink(product_id=product_id, application_id=application_id))
    await session.commit()
    return {"detail": "Linked"}


@router.delete("/products/{product_id}/applications/{application_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def unlink_product_application(
    product_id: uuid.UUID,
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    application = await session.get(Application, application_id)
    if not application or not _tenant_visible(application, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Application not found")
    link = (await session.exec(
        select(ProductApplicationLink).where(
            ProductApplicationLink.product_id == product_id,
            ProductApplicationLink.application_id == application_id,
        )
    )).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await session.delete(link)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Product ↔ Certifications
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/products/{product_id}/certifications", response_model=list[RelatedItemOut])
async def list_product_certifications(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product(product_id, session, current_user.tenant_id)
    await session.refresh(product, ["certifications"])
    return [_cert_out(c) for c in product.certifications if _tenant_visible(c, current_user.tenant_id)]


@router.post("/products/{product_id}/certifications/{certification_id}",
             status_code=status.HTTP_201_CREATED)
async def link_product_certification(
    product_id: uuid.UUID,
    certification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    certification = await session.get(Certification, certification_id)
    if not certification or not _tenant_visible(certification, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Certification not found")

    existing = (await session.exec(
        select(ProductCertificationLink).where(
            ProductCertificationLink.product_id == product_id,
            ProductCertificationLink.certification_id == certification_id,
        )
    )).first()
    if existing:
        return {"detail": "Already linked"}

    session.add(ProductCertificationLink(product_id=product_id, certification_id=certification_id))
    await session.commit()
    return {"detail": "Linked"}


@router.delete("/products/{product_id}/certifications/{certification_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def unlink_product_certification(
    product_id: uuid.UUID,
    certification_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    certification = await session.get(Certification, certification_id)
    if not certification or not _tenant_visible(certification, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Certification not found")
    link = (await session.exec(
        select(ProductCertificationLink).where(
            ProductCertificationLink.product_id == product_id,
            ProductCertificationLink.certification_id == certification_id,
        )
    )).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await session.delete(link)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Product ↔ FAQs
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/products/{product_id}/faqs", response_model=list[RelatedItemOut])
async def list_product_faqs(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product(product_id, session, current_user.tenant_id)
    await session.refresh(product, ["faqs"])
    return [_faq_out(f) for f in product.faqs if _tenant_visible(f, current_user.tenant_id)]


@router.post("/products/{product_id}/faqs/{faq_id}", status_code=status.HTTP_201_CREATED)
async def link_product_faq(
    product_id: uuid.UUID,
    faq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    faq = await session.get(FAQItem, faq_id)
    if not faq or not _tenant_visible(faq, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="FAQ not found")

    existing = (await session.exec(
        select(ProductFAQLink).where(
            ProductFAQLink.product_id == product_id,
            ProductFAQLink.faq_item_id == faq_id,
        )
    )).first()
    if existing:
        return {"detail": "Already linked"}

    session.add(ProductFAQLink(product_id=product_id, faq_item_id=faq_id))
    await session.commit()
    return {"detail": "Linked"}


@router.delete("/products/{product_id}/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_product_faq(
    product_id: uuid.UUID,
    faq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    faq = await session.get(FAQItem, faq_id)
    if not faq or not _tenant_visible(faq, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="FAQ not found")
    link = (await session.exec(
        select(ProductFAQLink).where(
            ProductFAQLink.product_id == product_id,
            ProductFAQLink.faq_item_id == faq_id,
        )
    )).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await session.delete(link)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Application ↔ FAQs
# ═══════════════════════════════════════════════════════════════════════════════

async def _get_application(app_id: uuid.UUID, session: AsyncSession, tenant_id: uuid.UUID | None = None) -> Application:
    app = await session.get(Application, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    _ensure_tenant_match(app, tenant_id, "Application not found")
    return app


@router.get("/applications/{application_id}/faqs", response_model=list[RelatedItemOut])
async def list_application_faqs(
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    app = await _get_application(application_id, session, current_user.tenant_id)
    await session.refresh(app, ["faqs"])
    return [_faq_out(f) for f in app.faqs if _tenant_visible(f, current_user.tenant_id)]


@router.post("/applications/{application_id}/faqs/{faq_id}",
             status_code=status.HTTP_201_CREATED)
async def link_application_faq(
    application_id: uuid.UUID,
    faq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_application(application_id, session, current_user.tenant_id)
    faq = await session.get(FAQItem, faq_id)
    if not faq or not _tenant_visible(faq, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="FAQ not found")

    existing = (await session.exec(
        select(ApplicationFAQLink).where(
            ApplicationFAQLink.application_id == application_id,
            ApplicationFAQLink.faq_item_id == faq_id,
        )
    )).first()
    if existing:
        return {"detail": "Already linked"}

    session.add(ApplicationFAQLink(application_id=application_id, faq_item_id=faq_id))
    await session.commit()
    return {"detail": "Linked"}


@router.delete("/applications/{application_id}/faqs/{faq_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def unlink_application_faq(
    application_id: uuid.UUID,
    faq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_application(application_id, session, current_user.tenant_id)
    faq = await session.get(FAQItem, faq_id)
    if not faq or not _tenant_visible(faq, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="FAQ not found")
    link = (await session.exec(
        select(ApplicationFAQLink).where(
            ApplicationFAQLink.application_id == application_id,
            ApplicationFAQLink.faq_item_id == faq_id,
        )
    )).first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    await session.delete(link)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Product ↔ Alternative Parts (self M2M — bidirectional auto-create)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/products/{product_id}/alternatives", response_model=list[RelatedItemOut])
async def list_product_alternatives(
    product_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    product = await _get_product(product_id, session, current_user.tenant_id)
    # Query both directions of the self-M2M
    links_a = (await session.exec(
        select(AlternativePartLink).where(AlternativePartLink.product_id == product_id)
    )).all()
    links_b = (await session.exec(
        select(AlternativePartLink).where(AlternativePartLink.alternative_product_id == product_id)
    )).all()
    seen: set[uuid.UUID] = set()
    result: list[RelatedItemOut] = []
    for link in links_a:
        if link.alternative_product_id not in seen:
            seen.add(link.alternative_product_id)
            alt = await session.get(Product, link.alternative_product_id)
            if alt and _tenant_visible(alt, current_user.tenant_id):
                result.append(RelatedItemOut(id=alt.id, name=alt.product_name, slug=alt.slug))
    for link in links_b:
        if link.product_id not in seen and link.product_id != product_id:
            seen.add(link.product_id)
            alt = await session.get(Product, link.product_id)
            if alt and _tenant_visible(alt, current_user.tenant_id):
                result.append(RelatedItemOut(id=alt.id, name=alt.product_name, slug=alt.slug))
    return result


@router.post("/products/{product_id}/alternatives/{alternative_id}",
             status_code=status.HTTP_201_CREATED)
async def link_product_alternative(
    product_id: uuid.UUID,
    alternative_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    if product_id == alternative_id:
        raise HTTPException(status_code=400, detail="Cannot link a product to itself")
    await _get_product(product_id, session, current_user.tenant_id)
    alternative = await session.get(Product, alternative_id)
    if not alternative or not _tenant_visible(alternative, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Alternative product not found")

    # Check both directions to avoid duplicates
    existing = (await session.exec(
        select(AlternativePartLink).where(
            ((AlternativePartLink.product_id == product_id) & (AlternativePartLink.alternative_product_id == alternative_id)) |
            ((AlternativePartLink.product_id == alternative_id) & (AlternativePartLink.alternative_product_id == product_id))
        )
    )).first()
    if existing:
        return {"detail": "Already linked"}

    # Bidirectional: create both directions
    session.add(AlternativePartLink(product_id=product_id, alternative_product_id=alternative_id))
    session.add(AlternativePartLink(product_id=alternative_id, alternative_product_id=product_id))
    await session.commit()
    return {"detail": "Linked (bidirectional)"}


@router.delete("/products/{product_id}/alternatives/{alternative_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def unlink_product_alternative(
    product_id: uuid.UUID,
    alternative_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_product(product_id, session, current_user.tenant_id)
    alternative = await session.get(Product, alternative_id)
    if not alternative or not _tenant_visible(alternative, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Alternative product not found")
    # Remove both directions
    for a, b in [(product_id, alternative_id), (alternative_id, product_id)]:
        link = (await session.exec(
            select(AlternativePartLink).where(
                AlternativePartLink.product_id == a,
                AlternativePartLink.alternative_product_id == b,
            )
        )).first()
        if link:
            await session.delete(link)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# Application ↔ Related Applications (self M2M — bidirectional)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/applications/{application_id}/related-applications",
            response_model=list[RelatedItemOut])
async def list_related_applications(
    application_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _get_application(application_id, session, current_user.tenant_id)
    links_a = (await session.exec(
        select(ApplicationRelatedLink).where(ApplicationRelatedLink.application_id == application_id)
    )).all()
    links_b = (await session.exec(
        select(ApplicationRelatedLink).where(ApplicationRelatedLink.related_application_id == application_id)
    )).all()
    seen: set[uuid.UUID] = set()
    result: list[RelatedItemOut] = []
    for link in links_a:
        if link.related_application_id not in seen:
            seen.add(link.related_application_id)
            rel = await session.get(Application, link.related_application_id)
            if rel and _tenant_visible(rel, current_user.tenant_id):
                result.append(RelatedItemOut(id=rel.id, name=rel.application_name, slug=rel.slug))
    for link in links_b:
        if link.application_id not in seen and link.application_id != application_id:
            seen.add(link.application_id)
            rel = await session.get(Application, link.application_id)
            if rel and _tenant_visible(rel, current_user.tenant_id):
                result.append(RelatedItemOut(id=rel.id, name=rel.application_name, slug=rel.slug))
    return result


@router.post("/applications/{application_id}/related-applications/{related_id}",
             status_code=status.HTTP_201_CREATED)
async def link_related_application(
    application_id: uuid.UUID,
    related_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    if application_id == related_id:
        raise HTTPException(status_code=400, detail="Cannot link an application to itself")
    await _get_application(application_id, session, current_user.tenant_id)
    related = await session.get(Application, related_id)
    if not related or not _tenant_visible(related, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Related application not found")

    existing = (await session.exec(
        select(ApplicationRelatedLink).where(
            ((ApplicationRelatedLink.application_id == application_id) & (ApplicationRelatedLink.related_application_id == related_id)) |
            ((ApplicationRelatedLink.application_id == related_id) & (ApplicationRelatedLink.related_application_id == application_id))
        )
    )).first()
    if existing:
        return {"detail": "Already linked"}

    session.add(ApplicationRelatedLink(application_id=application_id, related_application_id=related_id))
    session.add(ApplicationRelatedLink(application_id=related_id, related_application_id=application_id))
    await session.commit()
    return {"detail": "Linked (bidirectional)"}


@router.delete("/applications/{application_id}/related-applications/{related_id}",
               status_code=status.HTTP_204_NO_CONTENT)
async def unlink_related_application(
    application_id: uuid.UUID,
    related_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_content_editor),
):
    await _get_application(application_id, session, current_user.tenant_id)
    related = await session.get(Application, related_id)
    if not related or not _tenant_visible(related, current_user.tenant_id):
        raise HTTPException(status_code=404, detail="Related application not found")
    for a, b in [(application_id, related_id), (related_id, application_id)]:
        link = (await session.exec(
            select(ApplicationRelatedLink).where(
                ApplicationRelatedLink.application_id == a,
                ApplicationRelatedLink.related_application_id == b,
            )
        )).first()
        if link:
            await session.delete(link)
    await session.commit()

