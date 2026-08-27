"""Small production monitor for durable background-job health."""
import logging
from datetime import datetime, timedelta

import httpx
from sqlmodel import func, select

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.operational_job import OperationalJob
from app.services.email_service import send_email_result

logger = logging.getLogger(__name__)

_last_alert_signature: tuple[int, int] | None = None
_last_alert_at: datetime | None = None


async def check_operational_health() -> dict[str, int | bool]:
    global _last_alert_signature, _last_alert_at
    now = utcnow_naive()
    async with get_session_ctx() as db:
        failed = int((await db.exec(
            select(func.count()).select_from(OperationalJob).where(OperationalJob.status == "failed")
        )).one())
        stale = int((await db.exec(
            select(func.count()).select_from(OperationalJob).where(
                OperationalJob.status == "processing",
                OperationalJob.locked_at <= now - timedelta(minutes=settings.OPS_STALE_JOB_MINUTES),
            )
        )).one())
    healthy = failed < settings.OPS_FAILED_JOB_ALERT_THRESHOLD and stale == 0
    result: dict[str, int | bool] = {"failed": failed, "stale": stale, "healthy": healthy}
    signature = (failed, stale)
    cooldown_elapsed = (
        _last_alert_at is None
        or now - _last_alert_at >= timedelta(minutes=settings.OPS_ALERT_COOLDOWN_MINUTES)
    )
    email_alerting_ready = bool(
        settings.RESEND_API_KEY
        and settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST
        and settings.SALES_NOTIFY_EMAIL
        and not settings.EMAIL_DRY_RUN
    )
    should_alert = not healthy and (settings.OPS_ALERT_WEBHOOK_URL or email_alerting_ready) and (
        signature != _last_alert_signature or cooldown_elapsed
    )
    if should_alert:
        delivered = False
        try:
            if settings.OPS_ALERT_WEBHOOK_URL:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(settings.OPS_ALERT_WEBHOOK_URL, json={"event": "forgebase_operational_jobs_unhealthy", **result})
                    response.raise_for_status()
                delivered = True
            else:
                email_result = await send_email_result(
                    to=settings.SALES_NOTIFY_EMAIL,
                    subject="[ForgeBase] 背景工作異常告警",
                    text_body=f"failed={failed}\nstale={stale}\n請登入系統方後台檢查失敗工作。",
                    idempotency_key=f"ops-alert-{failed}-{stale}-{now:%Y%m%d%H%M}",
                    recipient_kind="internal",
                )
                delivered = email_result.success
        except Exception:
            logger.exception("Operational health alert delivery failed")
        if delivered:
            _last_alert_signature = signature
            _last_alert_at = now
    elif healthy:
        _last_alert_signature = None
        _last_alert_at = None
    return result
