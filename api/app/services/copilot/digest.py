"""
AI Copilot — Daily Digest Generator

Generates and sends a natural-language daily operations summary
to all tenants with activated daily_summary notifications.

Called by APScheduler at COPILOT_DAILY_SUMMARY_HOUR (default 08:00 Asia/Taipei).

Public API:
    await run_daily_digest()
"""
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
from app.models.visitor import Visitor
from app.services.notification_router import send_notification

logger = logging.getLogger(__name__)

_ADMIN_URL = settings.ADMIN_URL.rstrip("/")


async def _get_tenant_ids_with_active_digest(session: AsyncSession) -> list[uuid.UUID]:
    """Return distinct tenant_ids that have at least one active daily_summary pref."""
    result = await session.exec(
        select(NotificationPreference.tenant_id)
        .where(NotificationPreference.enabled == True)
        .where(NotificationPreference.notify_daily_summary == True)
        .distinct()
    )
    return list(result.all())


async def _collect_stats(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    include_growth: bool,
) -> dict:
    """Gather 24h stats for a specific tenant."""
    now = utcnow_naive()
    yesterday = now - timedelta(hours=24)

    # New RFQs in last 24h
    rfq_result = await session.exec(
        select(func.count(RFQRequest.id))
        .where(RFQRequest.tenant_id == tenant_id)
        .where(RFQRequest.created_at >= yesterday)
    )
    new_rfqs = rfq_result.one() or 0

    # High/urgent RFQs
    urgent_result = await session.exec(
        select(func.count(RFQRequest.id))
        .where(RFQRequest.tenant_id == tenant_id)
        .where(RFQRequest.created_at >= yesterday)
        .where(RFQRequest.priority.in_(["high", "urgent"]))
    )
    urgent_rfqs = urgent_result.one() or 0

    # Overdue RFQs (new status > 24h)
    overdue_result = await session.exec(
        select(func.count(RFQRequest.id))
        .where(RFQRequest.tenant_id == tenant_id)
        .where(RFQRequest.status == "new")
        .where(RFQRequest.created_at <= yesterday)
    )
    overdue_rfqs = overdue_result.one() or 0

    active_visitors = 0
    hot_visitors = 0
    if include_growth:
        # Visitor and intent metrics belong to the second-stage growth scope.
        visitor_result = await session.exec(
            select(func.count(Visitor.visitor_id))
            .where(Visitor.tenant_id == tenant_id)
            .where(Visitor.last_activity_at >= yesterday)
        )
        active_visitors = visitor_result.one() or 0

        hot_result = await session.exec(
            select(func.count(Visitor.visitor_id))
            .where(Visitor.tenant_id == tenant_id)
            .where(Visitor.intent_stage.in_(["hot", "sales_ready"]))
            .where(Visitor.last_activity_at >= yesterday)
        )
        hot_visitors = hot_result.one() or 0

    return {
        "new_rfqs": new_rfqs,
        "urgent_rfqs": urgent_rfqs,
        "overdue_rfqs": overdue_rfqs,
        "active_visitors": active_visitors,
        "hot_visitors": hot_visitors,
    }


def _format_digest(stats: dict, date_str: str, *, include_growth: bool) -> str:
    """Format a daily digest message."""
    new_rfqs = stats["new_rfqs"]
    urgent_rfqs = stats["urgent_rfqs"]
    overdue_rfqs = stats["overdue_rfqs"]
    active_visitors = stats["active_visitors"]
    hot_visitors = stats["hot_visitors"]

    # Build suggestions
    suggestions = []
    if overdue_rfqs > 0:
        suggestions.append(f"⚠️ {overdue_rfqs} 筆 RFQ 超過 24h 未回覆，建議立即處理")
    if include_growth and hot_visitors > 0:
        suggestions.append(f"🔥 {hot_visitors} 位高關注訪客活躍中，建議主動接觸")
    if include_growth and new_rfqs == 0 and active_visitors < 5:
        suggestions.append("💡 今日流量偏低，考慮發送 nurture email 喚回潛在客戶")

    suggestion_block = ""
    if suggestions:
        suggestion_block = "\n\n⚡ <b>AI 建議：</b>\n" + "\n".join(suggestions)

    rfq_line = f"{new_rfqs} 筆"
    if urgent_rfqs > 0:
        rfq_line += f"（{urgent_rfqs} 筆高優先 ⚠️）"
    if overdue_rfqs > 0:
        rfq_line += f"（{overdue_rfqs} 筆超時未回 🚨）"

    growth_lines = ""
    if include_growth:
        growth_lines = f"訪客：{active_visitors} 人\n高關注訪客：{hot_visitors} 人\n"
    return (
        f"📊 <b>每日營運摘要 — {date_str}</b>\n\n"
        f"{growth_lines}"
        f"新 RFQ：{rfq_line}\n"
        f"{suggestion_block}"
    )


async def run_daily_digest() -> dict:
    """
    Main entry point called by APScheduler.
    Returns: {tenants_processed: N, notifications_sent: N}
    """
    stats_summary = {"tenants_processed": 0, "notifications_sent": 0}
    date_str = utcnow_naive().strftime("%Y/%m/%d")

    async with get_session_ctx() as session:
        tenant_ids = await _get_tenant_ids_with_active_digest(session)

    for tenant_id in tenant_ids:
        try:
            async with get_session_ctx() as session:
                from app.models.tenant import Tenant
                from app.services.capability_access import tenant_has_feature

                tenant = await session.get(Tenant, tenant_id)
                if not tenant or not tenant_has_feature(tenant, "notifications"):
                    continue
                include_growth = tenant_has_feature(tenant, "full_tracking")
                stats = await _collect_stats(
                    session,
                    tenant_id,
                    include_growth=include_growth,
                )

            message = _format_digest(stats, date_str, include_growth=include_growth)
            buttons = [
                {"label": "開啟後台", "url": f"{_ADMIN_URL}/backend/overview"},
            ]

            sent = await send_notification(
                tenant_id=tenant_id,
                event_type="daily_summary",
                message=message,
                buttons=buttons,
            )
            stats_summary["tenants_processed"] += 1
            stats_summary["notifications_sent"] += sent

        except Exception as exc:
            logger.error("Daily digest failed for tenant %s: %s", tenant_id, exc)

    logger.info("Daily digest complete: %s", stats_summary)
    return stats_summary
