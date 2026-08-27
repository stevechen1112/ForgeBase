from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.knowledge import KnowledgeSource, KnowledgeSyncJob
from app.models.product import Product
from app.models.tenant import Tenant
from app.services.knowledge_compile import (
    compile_source,
    reindex_published_tenant,
    tombstone_source,
)

logger = logging.getLogger(__name__)

_MODEL_SOURCE_TYPE = {
    "Product": "product",
    "ProductCategory": "category",
    "Application": "application",
    "Capability": "capability",
    "Certification": "certification",
    "FAQItem": "faq",
    "Page": "page",
    "ContentAsset": "asset",
}


def source_type_for(item: object) -> str | None:
    return _MODEL_SOURCE_TYPE.get(item.__class__.__name__)


async def sync_knowledge_now(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    item: object | None = None,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    action: str = "compile",
) -> None:
    """Compile or hide a source in the current transaction.

    Call this after the CMS/asset row is flushed so the next question
    sees the new public text, or immediately loses withdrawn text.
    """
    if tenant_id is None:
        return
    if item is not None:
        source_type = source_type or source_type_for(item)
        source_id = source_id or getattr(item, "id", None)
    if not source_type or not source_id:
        return
    if action == "tombstone":
        await tombstone_source(session, tenant_id=tenant_id, source_type=source_type, source_id=source_id)
        return
    await compile_source(session, tenant_id=tenant_id, source_type=source_type, source_id=source_id)


async def process_knowledge_sync_jobs(limit: int = 20) -> dict[str, int]:
    stats = {"completed": 0, "failed": 0}
    async with get_session_ctx() as session:
        now = utcnow_naive()
        jobs = list(
            (
                await session.exec(
                    select(KnowledgeSyncJob)
                    .where(
                        KnowledgeSyncJob.status == "queued",
                        KnowledgeSyncJob.available_at <= now,
                    )
                    .order_by(KnowledgeSyncJob.available_at)
                    .limit(limit)
                )
            ).all()
        )
        for job in jobs:
            job.status = "running"
            job.attempts += 1
            job.updated_at = now
            session.add(job)
        await session.commit()

        for job in jobs:
            try:
                if job.action == "tombstone":
                    await tombstone_source(
                        session,
                        tenant_id=job.tenant_id,
                        source_type=job.source_type,
                        source_id=job.source_id,
                    )
                else:
                    await compile_source(
                        session,
                        tenant_id=job.tenant_id,
                        source_type=job.source_type,
                        source_id=job.source_id,
                    )
                job.status = "succeeded"
                job.last_error = None
                stats["completed"] += 1
            except Exception as exc:
                logger.exception("knowledge sync job failed: %s", job.id)
                job.last_error = str(exc)[:2000]
                job.status = "failed" if job.attempts >= 5 else "queued"
                job.available_at = utcnow_naive() + timedelta(minutes=2 ** min(job.attempts, 5))
                stats["failed"] += 1
            job.updated_at = utcnow_naive()
            session.add(job)
            await session.commit()
        backfill = await backfill_missing_knowledge(session)
        stats["backfilled_tenants"] = backfill["tenants"]
        await session.commit()
    return stats


async def backfill_missing_knowledge(session: AsyncSession) -> dict[str, int]:
    """Index published CMS that was never compiled, e.g. content from before this release."""
    stats = {"tenants": 0}
    tenants = list((await session.exec(select(Tenant.id))).all())
    for tenant_id in tenants:
        published = (
            await session.exec(
                select(func.count(Product.id)).where(
                    Product.tenant_id == tenant_id,
                    Product.status == "published",
                )
            )
        ).one()
        indexed = (
            await session.exec(
                select(func.count(KnowledgeSource.id)).where(
                    KnowledgeSource.tenant_id == tenant_id,
                    KnowledgeSource.source_type == "product",
                    KnowledgeSource.status == "indexed",
                )
            )
        ).one()
        if int(published or 0) <= int(indexed or 0):
            continue
        await reindex_published_tenant(session, tenant_id)
        stats["tenants"] += 1
    return stats


async def ensure_tenant_knowledge_index(session: AsyncSession, tenant_id: uuid.UUID | None) -> None:
    if tenant_id is None:
        return
    indexed_products = int(
        (
            await session.exec(
                select(func.count(KnowledgeSource.id)).where(
                    KnowledgeSource.tenant_id == tenant_id,
                    KnowledgeSource.source_type == "product",
                    KnowledgeSource.status == "indexed",
                )
            )
        ).one()
        or 0
    )
    published = int(
        (
            await session.exec(
                select(func.count(Product.id)).where(
                    Product.tenant_id == tenant_id,
                    Product.status == "published",
                )
            )
        ).one()
        or 0
    )
    indexed_any = int(
        (
            await session.exec(
                select(func.count(KnowledgeSource.id)).where(
                    KnowledgeSource.tenant_id == tenant_id,
                    KnowledgeSource.status == "indexed",
                )
            )
        ).one()
        or 0
    )
    if published <= indexed_products and indexed_any > 0:
        return
    if published == 0 and indexed_any > 0:
        return
    await reindex_published_tenant(session, tenant_id)
    await session.commit()
