"""
Scheduled Publishing Service

掃描 status = 'scheduled' 且 published_at <= now() 的商品，
自動將狀態切換為 'published'。
由 APScheduler 每分鐘呼叫一次。
"""
import logging
from datetime import datetime, timezone

from sqlmodel import col, select

from app.db.session import get_session_ctx
from app.models.product import Product

logger = logging.getLogger("forgebase.scheduler.publishing")


async def run_scheduled_publishing() -> dict:
    """
    Publish all products whose publish time has arrived.
    Returns: {"published": N}
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # DB stores naive UTC
    published_count = 0

    async with get_session_ctx() as session:
        stmt = select(Product).where(
            col(Product.status) == "scheduled",
            col(Product.published_at) <= now,
        )
        result = await session.exec(stmt)
        products = result.all()

        for product in products:
            product.status = "published"
            product.updated_at = now
            session.add(product)
            logger.info(
                "Auto-published product id=%s name=%r scheduled_at=%s",
                product.id,
                product.product_name,
                product.published_at,
            )
            published_count += 1

        if published_count:
            await session.commit()
            from app.services.knowledge_sync import sync_knowledge_now

            for product in products:
                if product.tenant_id is None:
                    continue
                await sync_knowledge_now(session, tenant_id=product.tenant_id, item=product)
            await session.commit()

    return {"published": published_count}
