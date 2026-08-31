"""Deterministic daily operations summary for sales teams."""

import logging
import uuid
from datetime import timedelta

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.notification_preference import NotificationPreference
from app.models.rfq_request import RFQRequest
from app.models.tenant import Tenant
from app.models.visitor import Visitor
from app.services.capability_access import tenant_has_feature
from app.services.notification_router import send_notification

logger = logging.getLogger(__name__)


async def _enabled_tenant_ids(session: AsyncSession) -> list[uuid.UUID]:
    result = await session.exec(
        select(NotificationPreference.tenant_id)
        .where(NotificationPreference.enabled.is_(True))
        .where(NotificationPreference.notify_daily_summary.is_(True))
        .distinct()
    )
    return list(result.all())


async def _collect_stats(
    session: AsyncSession, tenant_id: uuid.UUID, *, include_growth: bool
) -> dict[str, int]:
    since = utcnow_naive() - timedelta(hours=24)

    async def count(statement) -> int:
        return int((await session.exec(statement)).one() or 0)

    stats = {
        "new_rfqs": await count(
            select(func.count(RFQRequest.id)).where(
                RFQRequest.tenant_id == tenant_id, RFQRequest.created_at >= since
            )
        ),
        "urgent_rfqs": await count(
            select(func.count(RFQRequest.id)).where(
                RFQRequest.tenant_id == tenant_id,
                RFQRequest.created_at >= since,
                RFQRequest.priority.in_(["high", "urgent"]),
            )
        ),
        "overdue_rfqs": await count(
            select(func.count(RFQRequest.id)).where(
                RFQRequest.tenant_id == tenant_id,
                RFQRequest.status == "new",
                RFQRequest.created_at <= since,
            )
        ),
        "active_visitors": 0,
        "hot_visitors": 0,
    }
    if include_growth:
        stats["active_visitors"] = await count(
            select(func.count(Visitor.visitor_id)).where(
                Visitor.tenant_id == tenant_id, Visitor.last_activity_at >= since
            )
        )
        stats["hot_visitors"] = await count(
            select(func.count(Visitor.visitor_id)).where(
                Visitor.tenant_id == tenant_id,
                Visitor.intent_stage.in_(["hot", "sales_ready"]),
                Visitor.last_activity_at >= since,
            )
        )
    return stats


def _format_summary(stats: dict[str, int], date_text: str, *, include_growth: bool) -> str:
    rfq_line = f"{stats['new_rfqs']} 筆"
    if stats["urgent_rfqs"]:
        rfq_line += f"（高優先 {stats['urgent_rfqs']} 筆）"
    reminders: list[str] = []
    if stats["overdue_rfqs"]:
        reminders.append(f"{stats['overdue_rfqs']} 筆詢價超過 24 小時未回覆")
    if include_growth and stats["hot_visitors"]:
        reminders.append(f"{stats['hot_visitors']} 位高關注買家近 24 小時仍有活動")
    growth = ""
    if include_growth:
        growth = (
            f"網站活躍買家：{stats['active_visitors']} 位\n"
            f"高關注買家：{stats['hot_visitors']} 位\n"
        )
    reminder_text = "\n".join(f"待處理：{item}" for item in reminders)
    return (
        f"每日營運摘要 — {date_text}\n\n"
        f"{growth}新詢價：{rfq_line}"
        + (f"\n\n{reminder_text}" if reminder_text else "")
    )


async def run_daily_summary() -> dict[str, int]:
    result = {"tenants_processed": 0, "notifications_sent": 0}
    async with get_session_ctx() as session:
        tenant_ids = await _enabled_tenant_ids(session)

    for tenant_id in tenant_ids:
        try:
            async with get_session_ctx() as session:
                tenant = await session.get(Tenant, tenant_id)
                if not tenant or not tenant_has_feature(tenant, "notifications"):
                    continue
                include_growth = tenant_has_feature(tenant, "full_tracking")
                stats = await _collect_stats(
                    session, tenant_id, include_growth=include_growth
                )
            sent = await send_notification(
                tenant_id=tenant_id,
                event_type="daily_summary",
                message=_format_summary(
                    stats,
                    utcnow_naive().strftime("%Y/%m/%d"),
                    include_growth=include_growth,
                ),
                buttons=[
                    {
                        "label": "開啟後台",
                        "url": f"{settings.ADMIN_URL.rstrip('/')}/backend/overview",
                    }
                ],
            )
            result["tenants_processed"] += 1
            result["notifications_sent"] += sent
        except Exception:
            logger.exception("Daily operations summary failed tenant=%s", tenant_id)
    logger.info("Daily operations summary complete: %s", result)
    return result
