"""Persistent SLO sampling, incident creation, and alert delivery."""

import logging
import uuid

import httpx

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.observability import OperationalIncident, OperationalIncidentEvent
from app.services.email_service import send_email_result
from app.services.observability import collect_observability_snapshot

logger = logging.getLogger(__name__)


async def _deliver_incident_alert(
    incident: OperationalIncident,
) -> tuple[bool, str | None]:
    email_alerting_ready = bool(
        settings.RESEND_API_KEY
        and settings.EMAIL_INTERNAL_RECIPIENT_ALLOWLIST
        and settings.SALES_NOTIFY_EMAIL
        and not settings.EMAIL_DRY_RUN
    )
    if not settings.OPS_ALERT_WEBHOOK_URL and not email_alerting_ready:
        return False, "alert_destination_not_configured"
    try:
        if settings.OPS_ALERT_WEBHOOK_URL:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    settings.OPS_ALERT_WEBHOOK_URL,
                    json={
                        "event": "forgebase_operational_incident",
                        "incident_id": str(incident.id),
                        "incident_type": incident.incident_type,
                        "severity": incident.severity,
                        "status": incident.status,
                        "title": incident.title,
                        "metrics": incident.metrics,
                    },
                )
                response.raise_for_status()
            return True, None
        result = await send_email_result(
            to=settings.SALES_NOTIFY_EMAIL,
            subject=f"[ForgeBase][{incident.severity.upper()}] {incident.title}",
            text_body=(
                f"incident={incident.id}\nstatus={incident.status}\n"
                f"summary={incident.summary}\n請登入系統方後台處理。"
            ),
            idempotency_key=f"incident-alert-{incident.id}-{incident.occurrence_count}",
            recipient_kind="internal",
        )
        return result.success, result.error
    except Exception as exc:
        logger.exception("Operational incident alert delivery failed")
        return False, type(exc).__name__


async def check_operational_health() -> dict:
    async with get_session_ctx() as db:
        snapshot = await collect_observability_snapshot(db)

    for raw_id in snapshot.pop("notification_candidates"):
        incident_id = uuid.UUID(raw_id)
        async with get_session_ctx() as db:
            incident = await db.get(OperationalIncident, incident_id)
            if not incident or incident.status == "resolved":
                continue
            delivered, error = await _deliver_incident_alert(incident)
            if error == "alert_destination_not_configured":
                continue
            now = utcnow_naive()
            # Cool down both successful and failed attempts. Delivery failures are
            # visible in the incident console and must not cause a five-minute storm.
            incident.last_notified_at = now
            if delivered:
                incident.notification_error = None
                action = "notification_sent"
            else:
                incident.notification_error = error or "delivery_failed"
                action = "notification_failed"
            incident.updated_at = now
            db.add(incident)
            db.add(
                OperationalIncidentEvent(
                    incident_id=incident.id,
                    action=action,
                    detail={
                        "channel": "webhook"
                        if settings.OPS_ALERT_WEBHOOK_URL
                        else "email"
                    },
                )
            )
            await db.commit()

    metrics = {metric["key"]: metric for metric in snapshot["metrics"]}
    return {
        **snapshot,
        "failed": int(metrics["failed_operational_jobs"]["actual"]),
        "stale": int(metrics["stale_queue_claims"]["actual"]),
        # Insufficient low-traffic evidence is an explicit at-risk state, but it is
        # not an active outage and must not trigger scheduler error logging.
        "healthy": snapshot["status"] != "breached",
    }
