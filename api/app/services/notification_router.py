"""
Notification Router — unified dispatch for all AI Copilot notifications.

Usage:
    await send_notification(
        tenant_id=tenant_id,
        event_type="new_rfq",
        event_ref_id=rfq_id,
        message="...",
        buttons=[{"label": "查看後台", "url": "..."}],
    )

The router:
1. Queries notification_preferences for enabled users of this tenant / event type
2. Checks quiet hours
3. Checks deduplication (same event_ref_id + event_type in last 5 min)
4. Sends via the appropriate channel
5. Writes a notification_log row
"""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.notification_preference import NotificationPreference
from app.models.notification_log import NotificationLog
from app.services.channels.telegram import TelegramChannel

logger = logging.getLogger(__name__)

# Rate-limit: same (event_type, event_ref_id) → 5-minute cooldown
_RATE_LIMIT_MINUTES = 5

_CHANNEL_MAP = {
    "telegram": TelegramChannel(),
}

# Maps event_type → preference column name on NotificationPreference
_EVENT_PREF_COL = {
    "new_rfq": "notify_new_rfq",
    "hot_visitor": "notify_hot_visitor",
    "daily_summary": "notify_daily_summary",
    "churn_risk": "notify_churn_risk",
    "chat_handoff": "notify_chat_handoff",
    "content_suggestion": "notify_content_suggestion",
}


def _is_quiet_hours(pref: NotificationPreference) -> bool:
    """Returns True if current time falls within the user's quiet hours."""
    if not pref.quiet_hours_start or not pref.quiet_hours_end:
        return False
    now = datetime.now().strftime("%H:%M")
    start = pref.quiet_hours_start
    end = pref.quiet_hours_end
    if start <= end:
        return start <= now <= end
    # Overnight: e.g. 22:00 → 08:00
    return now >= start or now <= end


async def _is_rate_limited(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    event_type: str,
    event_ref_id: Optional[uuid.UUID],
) -> bool:
    """True if the same event was already sent in the last RATE_LIMIT_MINUTES."""
    if event_ref_id is None:
        return False
    cutoff = utcnow_naive() - timedelta(minutes=_RATE_LIMIT_MINUTES)
    q = (
        select(NotificationLog)
        .where(NotificationLog.tenant_id == tenant_id)
        .where(NotificationLog.event_type == event_type)
        .where(NotificationLog.event_ref_id == event_ref_id)
        .where(NotificationLog.sent_at >= cutoff)
        .where(NotificationLog.status == "sent")
        .limit(1)
    )
    result = await session.exec(q)
    return result.first() is not None


async def _log_notification(
    session: AsyncSession,
    tenant_id: Optional[uuid.UUID],
    user_id: Optional[uuid.UUID],
    channel: str,
    event_type: str,
    event_ref_id: Optional[uuid.UUID],
    message: str,
    status: str,
    error_detail: Optional[str] = None,
) -> None:
    log = NotificationLog(
        tenant_id=tenant_id,
        user_id=user_id,
        channel=channel,
        event_type=event_type,
        event_ref_id=event_ref_id,
        message_preview=message[:500] if message else None,
        status=status,
        error_detail=error_detail,
    )
    session.add(log)
    await session.commit()


async def send_notification(
    tenant_id: uuid.UUID,
    event_type: str,
    message: str,
    event_ref_id: Optional[uuid.UUID] = None,
    buttons: Optional[list[dict]] = None,
) -> int:
    """
    Dispatch a notification to all enabled subscribers for this tenant + event type.
    Returns number of successfully sent notifications.
    """
    pref_col = _EVENT_PREF_COL.get(event_type)
    sent_count = 0

    async with get_session_ctx() as session:
        # Check rate limit (tenant-wide, not per-user)
        if await _is_rate_limited(session, tenant_id, event_type, event_ref_id):
            logger.debug(
                "Notification rate-limited: tenant=%s event=%s ref=%s",
                tenant_id, event_type, event_ref_id,
            )
            return 0

        # Fetch active preferences for this tenant
        q = (
            select(NotificationPreference)
            .where(NotificationPreference.tenant_id == tenant_id)
            .where(NotificationPreference.enabled == True)
        )
        result = await session.exec(q)
        prefs = result.all()

        for pref in prefs:
            # Check per-event toggle
            if pref_col and not getattr(pref, pref_col, True):
                continue

            # Check quiet hours
            if _is_quiet_hours(pref):
                await _log_notification(
                    session, tenant_id, pref.user_id,
                    pref.channel, event_type, event_ref_id, message,
                    "skipped_quiet_hours",
                )
                continue

            # Resolve channel handler
            handler = _CHANNEL_MAP.get(pref.channel)
            if not handler:
                logger.debug("Unknown channel: %s", pref.channel)
                continue

            # Parse recipient config
            try:
                recipient_config = json.loads(pref.channel_config or "{}")
            except (ValueError, TypeError):
                recipient_config = {}

            # Send
            try:
                ok = await handler.send(recipient_config, message, buttons)
                status = "sent" if ok else "failed"
                if ok:
                    sent_count += 1
            except Exception as exc:
                ok = False
                status = "failed"
                error_detail = str(exc)[:300]
                logger.error(
                    "Notification send error (channel=%s, user=%s): %s",
                    pref.channel, pref.user_id, exc,
                )
            else:
                error_detail = None

            await _log_notification(
                session, tenant_id, pref.user_id,
                pref.channel, event_type, event_ref_id, message,
                status, None if ok else (error_detail or "send returned False"),
            )

    return sent_count
