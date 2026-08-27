from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.core.locale import normalize_locale
from app.models.application import Application
from app.models.capability import Capability
from app.models.certification import Certification
from app.models.content_asset import ContentAsset
from app.models.faq_item import FAQItem
from app.models.knowledge import KnowledgeChunk, KnowledgeSource
from app.models.page import Page
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.services.knowledge_extract import (
    NeedsOCR,
    extract_document_pages,
    is_indexable_document,
)
from app.services.knowledge_text import (
    chunk_text,
    content_hash,
    is_legal_page,
    metadata_dumps,
    strip_html,
)

logger = logging.getLogger(__name__)

CMS_SOURCE_TYPES = {
    "product",
    "category",
    "application",
    "capability",
    "certification",
    "faq",
    "page",
}


class CompileSkip(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _tenant_ok(entity: Any, tenant_id: uuid.UUID) -> bool:
    entity_tenant = getattr(entity, "tenant_id", None)
    return entity_tenant in (None, tenant_id)


def _published(entity: Any) -> bool:
    status = getattr(entity, "status", None)
    if status is None:
        return True
    if isinstance(entity, Certification):
        return status == "active"
    return status == "published"


def _localized_url(locale: str | None, path: str) -> str:
    route_locale = normalize_locale(locale)
    return path if route_locale == "en" else f"/{route_locale}{path}"


def compile_product_document(
    product: Product,
    category_name: str = "",
    category_slug: str = "",
) -> dict[str, Any]:
    specs = strip_html(product.specifications)
    body = "\n".join(
        part
        for part in (
            f"Product name: {product.product_name}",
            f"Model number: {product.model_number}",
            f"Category: {category_name}" if category_name else "",
            strip_html(product.short_description),
            strip_html(product.full_description),
            f"Specifications: {specs}" if specs else "",
            strip_html(product.seo_description),
        )
        if part
    )
    return {
        "title": product.product_name,
        "locale": normalize_locale(product.locale or "en"),
        "url": _localized_url(
            product.locale,
            f"/products/{category_slug}/{product.slug}" if category_slug else "/products",
        ),
        "text": body,
        "metadata": {"model_number": product.model_number, "product_name": product.product_name},
    }


def compile_category_document(category: ProductCategory) -> dict[str, Any]:
    body = "\n".join(
        part
        for part in (
            f"Category: {category.category_name}",
            strip_html(category.description),
            strip_html(category.seo_description),
        )
        if part
    )
    return {
        "title": category.category_name,
        "locale": normalize_locale(category.locale or "en"),
        "url": _localized_url(category.locale, f"/products/{category.slug}"),
        "text": body,
        "metadata": {"category_name": category.category_name},
    }


def compile_application_document(application: Application) -> dict[str, Any]:
    body = "\n".join(
        part
        for part in (
            f"Application: {application.application_name}",
            f"Industry: {application.industry}",
            strip_html(application.description),
            strip_html(application.challenge),
            strip_html(application.solution),
            strip_html(application.seo_description),
        )
        if part
    )
    return {
        "title": application.application_name,
        "locale": normalize_locale(application.locale or "en"),
        "url": _localized_url(application.locale, f"/applications/{application.slug}"),
        "text": body,
        "metadata": {"industry": application.industry},
    }


def compile_capability_document(capability: Capability) -> dict[str, Any]:
    body = "\n".join(
        part
        for part in (
            f"Capability: {capability.capability_name}",
            strip_html(capability.short_description),
            strip_html(capability.detail),
            strip_html(capability.metrics),
        )
        if part
    )
    return {
        "title": capability.capability_name,
        "locale": normalize_locale(capability.locale or "en"),
        "url": _localized_url(capability.locale, f"/capabilities/{capability.slug}"),
        "text": body,
        "metadata": {},
    }


def compile_certification_document(cert: Certification) -> dict[str, Any]:
    body = "\n".join(
        part
        for part in (
            f"Certification: {cert.cert_name}",
            f"Issuer: {cert.issuer}" if cert.issuer else "",
            f"Number: {cert.cert_number}" if cert.cert_number else "",
            strip_html(cert.description),
        )
        if part
    )
    return {
        "title": cert.cert_name,
        "locale": normalize_locale(cert.locale or "en"),
        "url": _localized_url(cert.locale, f"/certifications/{cert.slug}"),
        "text": body,
        "metadata": {"cert_name": cert.cert_name},
    }


def compile_faq_document(faq: FAQItem) -> dict[str, Any]:
    body = f"Question: {faq.question}\nAnswer: {strip_html(faq.answer)}"
    return {
        "title": faq.question,
        "locale": normalize_locale(faq.locale or "en"),
        "url": _localized_url(
            faq.locale,
            f"/faq/{faq.category_tag}" if faq.category_tag else "/faq",
        ),
        "text": body,
        "metadata": {},
    }


def compile_page_document(page: Page) -> dict[str, Any]:
    if is_legal_page(page.slug, page.page_type):
        raise CompileSkip("legal_page")
    body = "\n".join(
        part
        for part in (
            f"Page: {page.title}",
            strip_html(page.subtitle),
            strip_html(page.body),
            strip_html(page.seo_description),
        )
        if part
    )
    return {
        "title": page.title,
        "locale": normalize_locale(page.locale or "en"),
        "url": _localized_url(
            page.locale,
            f"/{page.slug}" if page.slug and page.slug != "home" else "/",
        ),
        "text": body,
        "metadata": {"page_type": page.page_type},
    }


async def _load_entity(session: AsyncSession, source_type: str, source_id: uuid.UUID) -> Any | None:
    model = {
        "product": Product,
        "category": ProductCategory,
        "application": Application,
        "capability": Capability,
        "certification": Certification,
        "faq": FAQItem,
        "page": Page,
        "asset": ContentAsset,
    }.get(source_type)
    if model is None:
        return None
    return await session.get(model, source_id)


async def _compile_cms(session: AsyncSession, source_type: str, entity: Any) -> dict[str, Any]:
    if source_type == "product":
        category_name = ""
        category_slug = ""
        if entity.category_id:
            category = await session.get(ProductCategory, entity.category_id)
            if category and _tenant_ok(category, entity.tenant_id):
                category_name = category.category_name
                category_slug = category.slug
        return compile_product_document(entity, category_name, category_slug)
    if source_type == "category":
        return compile_category_document(entity)
    if source_type == "application":
        return compile_application_document(entity)
    if source_type == "capability":
        return compile_capability_document(entity)
    if source_type == "certification":
        return compile_certification_document(entity)
    if source_type == "faq":
        return compile_faq_document(entity)
    if source_type == "page":
        return compile_page_document(entity)
    raise CompileSkip("unknown_source_type")


def _upload_roots():
    from pathlib import Path

    return (
        Path("/app/uploads"),
        Path(__file__).resolve().parents[2] / "uploads",
    )


async def _read_asset_bytes(asset: ContentAsset) -> bytes:
    for local_root in _upload_roots():
        local_path = local_root / asset.r2_key
        if local_path.is_file():
            return local_path.read_bytes()

    from app.core.config import settings

    if settings.R2_ACCOUNT_ID and settings.R2_ACCESS_KEY_ID:
        import asyncio

        from app.api.v1.endpoints.assets import _get_s3

        response = await asyncio.to_thread(
            _get_s3().get_object,
            Bucket=settings.R2_BUCKET_NAME,
            Key=asset.r2_key,
        )
        return response["Body"].read()
    raise NeedsOCR("asset_file_not_readable")


async def _compile_asset(asset: ContentAsset) -> dict[str, Any]:
    if not asset.is_indexable:
        raise CompileSkip("not_indexable")
    if not is_indexable_document(asset.mime_type, asset.original_filename):
        raise CompileSkip("not_a_text_document")
    data = await _read_asset_bytes(asset)
    pages = extract_document_pages(data, asset.mime_type, asset.original_filename)
    text_parts = []
    for page_number, page_text in pages:
        prefix = f"[page {page_number}] " if page_number else ""
        text_parts.append(prefix + page_text)
    title = asset.title or asset.seo_title or asset.original_filename
    return {
        "title": title,
        "locale": "en",
        "url": asset.public_url,
        "text": "\n".join(text_parts),
        "metadata": {"filename": asset.original_filename, "mime_type": asset.mime_type},
        "pages": pages,
        "page_count": len(pages),
    }


async def _upsert_source(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    locale: str,
) -> KnowledgeSource:
    existing = (
        await session.exec(
            select(KnowledgeSource).where(
                KnowledgeSource.tenant_id == tenant_id,
                KnowledgeSource.source_type == source_type,
                KnowledgeSource.source_id == source_id,
                KnowledgeSource.locale == locale,
            )
        )
    ).first()
    if existing:
        return existing
    source = KnowledgeSource(
        tenant_id=tenant_id,
        source_type=source_type,
        source_id=source_id,
        locale=locale,
        title=source_type,
    )
    session.add(source)
    await session.flush()
    return source


async def _replace_chunks(
    session: AsyncSession,
    source: KnowledgeSource,
    document: dict[str, Any],
) -> None:
    existing = (
        await session.exec(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id))
    ).all()
    for row in existing:
        await session.delete(row)
    await session.flush()

    pages = document.get("pages")
    if pages:
        chunk_index = 0
        for page_number, page_text in pages:
            for piece in chunk_text(page_text):
                session.add(
                    KnowledgeChunk(
                        source_id=source.id,
                        tenant_id=source.tenant_id,
                        chunk_index=chunk_index,
                        page_number=page_number,
                        text=piece,
                        metadata_json=metadata_dumps(document.get("metadata") or {}),
                    )
                )
                chunk_index += 1
        return

    for index, piece in enumerate(chunk_text(document["text"])):
        session.add(
            KnowledgeChunk(
                source_id=source.id,
                tenant_id=source.tenant_id,
                chunk_index=index,
                page_number=None,
                text=piece,
                metadata_json=metadata_dumps(document.get("metadata") or {}),
            )
        )


async def tombstone_source(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
    locale: str | None = None,
) -> None:
    """Remove live chunks immediately so the next question cannot see them."""
    statement = select(KnowledgeSource).where(
        KnowledgeSource.tenant_id == tenant_id,
        KnowledgeSource.source_type == source_type,
        KnowledgeSource.source_id == source_id,
    )
    if locale:
        statement = statement.where(KnowledgeSource.locale == normalize_locale(locale))
    sources = list((await session.exec(statement)).all())
    for source in sources:
        chunks = (
            await session.exec(select(KnowledgeChunk).where(KnowledgeChunk.source_id == source.id))
        ).all()
        for chunk in chunks:
            await session.delete(chunk)
        source.status = "tombstoned"
        source.updated_at = utcnow_naive()
        source.index_error = None
        session.add(source)


async def compile_source(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    source_type: str,
    source_id: uuid.UUID,
) -> KnowledgeSource | None:
    entity = await _load_entity(session, source_type, source_id)
    if entity is None or not _tenant_ok(entity, tenant_id):
        await tombstone_source(session, tenant_id=tenant_id, source_type=source_type, source_id=source_id)
        return None

    locale = normalize_locale(getattr(entity, "locale", None) or "en")
    source = await _upsert_source(
        session,
        tenant_id=tenant_id,
        source_type=source_type,
        source_id=source_id,
        locale=locale,
    )

    try:
        if source_type == "asset":
            if not _published_asset(entity):
                raise CompileSkip("asset_not_public")
            if (
                source.status == "indexed"
                and entity.sha256
                and source.content_hash == entity.sha256
            ):
                return source
            document = await _compile_asset(entity)
            entity.index_status = "indexed"
            entity.index_error = None
            session.add(entity)
        else:
            if not _published(entity):
                raise CompileSkip("not_published")
            document = await _compile_cms(session, source_type, entity)
        if not strip_html(document.get("text")):
            raise CompileSkip("empty_document")
    except NeedsOCR as exc:
        await tombstone_source(
            session, tenant_id=tenant_id, source_type=source_type, source_id=source_id, locale=locale
        )
        source = await _upsert_source(
            session,
            tenant_id=tenant_id,
            source_type=source_type,
            source_id=source_id,
            locale=locale,
        )
        source.status = "failed"
        source.index_error = "needs_ocr"
        source.updated_at = utcnow_naive()
        session.add(source)
        if source_type == "asset":
            entity.index_status = "needs_ocr"
            entity.index_error = str(exc)[:500]
            session.add(entity)
        return source
    except CompileSkip as exc:
        await tombstone_source(
            session, tenant_id=tenant_id, source_type=source_type, source_id=source_id, locale=locale
        )
        if source_type == "asset":
            entity.index_status = "withdrawn" if exc.reason in {"not_indexable", "asset_not_public"} else "not_indexed"
            entity.index_error = None
            session.add(entity)
        return None

    digest = (
        entity.sha256
        if source_type == "asset" and getattr(entity, "sha256", None)
        else content_hash(document["text"])
    )
    if source.status == "indexed" and source.content_hash == digest:
        return source
    source.title = document["title"][:300]
    source.canonical_url = document.get("url")
    source.content_hash = digest
    source.visibility = "public"
    source.status = "indexed"
    source.index_error = None
    source.page_count = document.get("page_count")
    source.updated_at = utcnow_naive()
    session.add(source)
    await _replace_chunks(session, source, document)
    return source


def _published_asset(asset: ContentAsset) -> bool:
    return bool(asset.is_indexable)


async def reindex_published_tenant(session: AsyncSession, tenant_id: uuid.UUID) -> int:
    """Compile every currently eligible public object. Used for first-chat backfill."""
    count = 0
    pairs: list[tuple[str, list[Any]]] = [
        ("product", list((await session.exec(select(Product).where(Product.tenant_id == tenant_id))).all())),
        (
            "category",
            list((await session.exec(select(ProductCategory).where(ProductCategory.tenant_id == tenant_id))).all()),
        ),
        (
            "application",
            list((await session.exec(select(Application).where(Application.tenant_id == tenant_id))).all()),
        ),
        (
            "capability",
            list((await session.exec(select(Capability).where(Capability.tenant_id == tenant_id))).all()),
        ),
        (
            "certification",
            list((await session.exec(select(Certification).where(Certification.tenant_id == tenant_id))).all()),
        ),
        ("faq", list((await session.exec(select(FAQItem).where(FAQItem.tenant_id == tenant_id))).all())),
        ("page", list((await session.exec(select(Page).where(Page.tenant_id == tenant_id))).all())),
        (
            "asset",
            list((await session.exec(select(ContentAsset).where(ContentAsset.tenant_id == tenant_id))).all()),
        ),
    ]
    for source_type, rows in pairs:
        for row in rows:
            try:
                result = await compile_source(
                    session, tenant_id=tenant_id, source_type=source_type, source_id=row.id
                )
                if result and result.status == "indexed":
                    count += 1
            except Exception:
                logger.exception("knowledge compile failed for %s %s", source_type, row.id)
    return count
