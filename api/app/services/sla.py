"""Timezone-aware RFQ handoff acceptance SLA.

設計依據：FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md §5.3「首回速度工程」。
SLA 以**買家時區的工作時間**（週一至週五 09:00–18:00 買家當地時間）計時：
台灣半夜送進來的歐美 RFQ，倒數從買家下一個上班時段開始算，
對業務才公平、對買家才有意義。
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DEFAULT_SLA_HOURS = 4.0
_BUSINESS_START_HOUR = 9
_BUSINESS_END_HOUR = 18

# 常見外銷市場 country code → IANA timezone（單一代表時區）
COUNTRY_TO_TZ: dict[str, str] = {
    "US": "America/New_York", "CA": "America/Toronto", "MX": "America/Mexico_City",
    "BR": "America/Sao_Paulo",
    "GB": "Europe/London", "IE": "Europe/Dublin",
    "DE": "Europe/Berlin", "FR": "Europe/Paris", "NL": "Europe/Amsterdam",
    "BE": "Europe/Brussels", "ES": "Europe/Madrid", "IT": "Europe/Rome",
    "PT": "Europe/Lisbon", "CH": "Europe/Zurich", "AT": "Europe/Vienna",
    "SE": "Europe/Stockholm", "NO": "Europe/Oslo", "DK": "Europe/Copenhagen",
    "FI": "Europe/Helsinki", "PL": "Europe/Warsaw", "CZ": "Europe/Prague",
    "JP": "Asia/Tokyo", "KR": "Asia/Seoul", "TW": "Asia/Taipei",
    "CN": "Asia/Shanghai", "HK": "Asia/Hong_Kong", "SG": "Asia/Singapore",
    "MY": "Asia/Kuala_Lumpur", "TH": "Asia/Bangkok", "VN": "Asia/Ho_Chi_Minh",
    "PH": "Asia/Manila", "ID": "Asia/Jakarta", "IN": "Asia/Kolkata",
    "AE": "Asia/Dubai", "SA": "Asia/Riyadh", "IL": "Asia/Jerusalem",
    "AU": "Australia/Sydney", "NZ": "Pacific/Auckland",
    "ZA": "Africa/Johannesburg", "EG": "Africa/Cairo",
}
_DEFAULT_TZ = "UTC"


def timezone_for_country(country: Optional[str]) -> str:
    if not country:
        return _DEFAULT_TZ
    return COUNTRY_TO_TZ.get(country.strip().upper(), _DEFAULT_TZ)


def add_business_hours(start_naive: datetime, hours: float, tz_name: str) -> datetime:
    """回傳 UTC-naive due time：從 start 起算 `hours` 個買家工作小時。

    規則：只計算週一至週五 09:00–18:00（買家當地時間）的時段；
    非工作時段送進來的單，從下一個上班時段開始計時。
    """
    tz = ZoneInfo(tz_name)
    local = start_naive.replace(tzinfo=ZoneInfo("UTC")).astimezone(tz)

    remaining = float(hours)
    cursor = local

    # 先推進到工作時段內
    while True:
        if cursor.weekday() >= 5:  # 週末 → 下個週一 09:00
            days_ahead = 7 - cursor.weekday()
            cursor = (cursor + timedelta(days=days_ahead)).replace(
                hour=_BUSINESS_START_HOUR, minute=0, second=0, microsecond=0
            )
            continue
        day_start = cursor.replace(hour=_BUSINESS_START_HOUR, minute=0, second=0, microsecond=0)
        day_end = cursor.replace(hour=_BUSINESS_END_HOUR, minute=0, second=0, microsecond=0)
        if cursor < day_start:
            cursor = day_start
            continue
        if cursor >= day_end:  # 下班後 → 隔天 09:00
            cursor = (cursor + timedelta(days=1)).replace(
                hour=_BUSINESS_START_HOUR, minute=0, second=0, microsecond=0
            )
            continue
        break

    while remaining > 0:
        day_end = cursor.replace(hour=_BUSINESS_END_HOUR, minute=0, second=0, microsecond=0)
        available = (day_end - cursor).total_seconds() / 3600.0
        if remaining <= available:
            cursor = cursor + timedelta(hours=remaining)
            remaining = 0
        else:
            remaining -= available
            cursor = (cursor + timedelta(days=1)).replace(
                hour=_BUSINESS_START_HOUR, minute=0, second=0, microsecond=0
            )
            while cursor.weekday() >= 5:
                cursor += timedelta(days=1)

    return cursor.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


async def load_sla_hours(tenant_id, db) -> float:
    """Per-tenant acceptance target; supports the legacy key during migration."""
    if not tenant_id:
        return DEFAULT_SLA_HOURS
    try:
        from app.services.ops_config import load_ops_config

        config = await load_ops_config(tenant_id, db)
        hours = config.get("sla_acceptance_hours") or config.get("sla_response_hours")
        if hours:
            return float(hours)
    except Exception:
        logger.debug("sla hours config unavailable, using default", exc_info=True)
    return DEFAULT_SLA_HOURS


async def compute_sla(body_country: Optional[str], tenant_id, created_at: datetime, db) -> tuple[str, datetime]:
    """Return ``(buyer_timezone, acceptance_due_at)`` for a new RFQ."""
    tz_name = timezone_for_country(body_country)
    hours = await load_sla_hours(tenant_id, db)
    return tz_name, add_business_hours(created_at, hours, tz_name)


async def scan_sla_breaches() -> dict:
    """每 15 分鐘由排程呼叫：

    - 即將超過接手期限且未提醒 → notify_rfq_reminder
    - 已超過接手期限 → acceptance_sla_breached=True + escalation
    """
    from sqlmodel import col, select

    from app.core.datetime import utcnow_naive
    from app.db.session import get_session_ctx
    from app.models.rfq_request import RFQRequest
    from app.services.notifications import notify_rfq_escalation, notify_rfq_reminder

    now = utcnow_naive()
    soon = now + timedelta(hours=1)
    stats = {"reminded": 0, "breached": 0}

    async with get_session_ctx() as db:
        open_rfqs = (
            await db.exec(
                select(RFQRequest).where(
                    col(RFQRequest.status).in_(["new", "assigned"]),
                    RFQRequest.accepted_at.is_(None),
                    RFQRequest.acceptance_due_at.is_not(None),
                )
            )
        ).all()

        for rfq in open_rfqs:
            if rfq.acceptance_due_at < now:
                if not rfq.acceptance_sla_breached:
                    rfq.acceptance_sla_breached = True
                    rfq.updated_at = now
                    db.add(rfq)
                    stats["breached"] += 1
                    try:
                        await notify_rfq_escalation(rfq.id)
                    except Exception:
                        logger.warning("escalation notify failed for %s", rfq.id, exc_info=True)
            elif rfq.acceptance_due_at <= soon and rfq.reminder_24h_sent_at is None:
                try:
                    await notify_rfq_reminder(rfq.id)
                    stats["reminded"] += 1
                except Exception:
                    logger.warning("reminder notify failed for %s", rfq.id, exc_info=True)

        await db.commit()
    return stats
