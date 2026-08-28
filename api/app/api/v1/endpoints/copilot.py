"""
Copilot API — Notification preferences CRUD + Telegram webhook receiver + Web chat.

Endpoints:
  GET    /copilot/preferences          — list user's notification preferences
  POST   /copilot/preferences          — create a preference row
  PUT    /copilot/preferences/{id}     — update toggles / quiet hours
  DELETE /copilot/preferences/{id}     — remove a channel preference
  GET    /copilot/notifications        — notification history (last 100)
  POST   /copilot/telegram/bind-start  — generate binding code + send to Telegram
  POST   /copilot/telegram/bind-verify — verify code and save chat_id
  POST   /copilot/webhook/telegram     — Telegram Bot webhook receiver (public)
  POST   /copilot/chat                 — Web chat: send message, get AI reply
  GET    /copilot/chat/history         — Web chat: fetch recent conversation history
  DELETE /copilot/chat/history         — Web chat: clear conversation history
"""
import json
import logging
import uuid
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    status,
)
from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.notification_log import NotificationLog
from app.models.notification_preference import NotificationPreference
from app.models.tenant import Tenant
from app.models.user import User
from app.services.capability_access import tenant_has_feature
from app.services.channels.telegram import TelegramChannel
from app.services.notification_channel_policy import (
    ACTIVE_NOTIFICATION_CHANNELS,
    retirement_candidate_for_channel,
)
from app.services.retirement_observability import record_retirement_usage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["Copilot"])
_telegram = TelegramChannel()

_VALID_CHANNELS = ACTIVE_NOTIFICATION_CHANNELS


# ── Schemas ───────────────────────────────────────────────────────────────────

class PreferenceIn(BaseModel):
    channel: str
    channel_config: dict = PydanticField(default_factory=dict)
    enabled: bool = True
    notify_new_rfq: bool = True
    notify_hot_visitor: bool = True
    notify_daily_summary: bool = True
    notify_churn_risk: bool = False
    notify_chat_handoff: bool = True
    notify_content_suggestion: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class PreferenceUpdate(BaseModel):
    enabled: Optional[bool] = None
    notify_new_rfq: Optional[bool] = None
    notify_hot_visitor: Optional[bool] = None
    notify_daily_summary: Optional[bool] = None
    notify_churn_risk: Optional[bool] = None
    notify_chat_handoff: Optional[bool] = None
    notify_content_suggestion: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class TelegramBindStart(BaseModel):
    telegram_chat_id: str  # user provides their Telegram chat_id or @username


class TelegramBindVerify(BaseModel):
    code: str


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_preference(
    pref_id: uuid.UUID,
    db: AsyncSession,
    user: User,
) -> NotificationPreference:
    pref = await db.get(NotificationPreference, pref_id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    if pref.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return pref


async def _block_retired_channel(
    db: AsyncSession,
    *,
    channel: str,
    event_name: str,
    tenant_id: uuid.UUID | None,
) -> None:
    candidate_key = retirement_candidate_for_channel(channel)
    if not candidate_key:
        return
    await record_retirement_usage(
        db,
        candidate_key=candidate_key,
        event_name=event_name,
        tenant_id=tenant_id,
    )
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=f"{channel.upper()} 通知入口已停用並進入退場觀察；通知核心仍正常保留。",
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/preferences", dependencies=[Depends(RequireFeature("notifications"))])
async def list_preferences(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.exec(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == current_user.id)
        .order_by(NotificationPreference.created_at)
    )
    prefs = result.all()
    return {
        "data": [
            {
                "id": str(p.id),
                "channel": p.channel,
                "channel_config": json.loads(p.channel_config or "{}"),
                "enabled": p.enabled,
                "notify_new_rfq": p.notify_new_rfq,
                "notify_hot_visitor": p.notify_hot_visitor,
                "notify_daily_summary": p.notify_daily_summary,
                "notify_churn_risk": p.notify_churn_risk,
                "notify_chat_handoff": p.notify_chat_handoff,
                "notify_content_suggestion": p.notify_content_suggestion,
                "quiet_hours_start": p.quiet_hours_start,
                "quiet_hours_end": p.quiet_hours_end,
                "retirement_disabled_at": (
                    p.retirement_disabled_at.isoformat()
                    if p.retirement_disabled_at
                    else None
                ),
                "created_at": p.created_at.isoformat(),
            }
            for p in prefs
        ]
    }


@router.post("/preferences", status_code=status.HTTP_201_CREATED, dependencies=[Depends(RequireFeature("notifications"))])
async def create_preference(
    body: PreferenceIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    normalized_channel = body.channel.strip().lower()
    await _block_retired_channel(
        db,
        channel=normalized_channel,
        event_name="preference_create_blocked",
        tenant_id=current_user.tenant_id,
    )
    if normalized_channel not in _VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Invalid channel. Allowed: {_VALID_CHANNELS}")

    pref = NotificationPreference(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        channel=normalized_channel,
        channel_config=json.dumps(body.channel_config),
        enabled=body.enabled,
        notify_new_rfq=body.notify_new_rfq,
        notify_hot_visitor=body.notify_hot_visitor,
        notify_daily_summary=body.notify_daily_summary,
        notify_churn_risk=body.notify_churn_risk,
        notify_chat_handoff=body.notify_chat_handoff,
        notify_content_suggestion=body.notify_content_suggestion,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
    )
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return {"data": {"id": str(pref.id)}}


@router.put("/preferences/{pref_id}", dependencies=[Depends(RequireFeature("notifications"))])
async def update_preference(
    pref_id: uuid.UUID,
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pref = await _get_preference(pref_id, db, current_user)
    await _block_retired_channel(
        db,
        channel=pref.channel,
        event_name="preference_update_blocked",
        tenant_id=current_user.tenant_id,
    )
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(pref, field, value)
    pref.updated_at = utcnow_naive()
    db.add(pref)
    await db.commit()
    return {"ok": True}


@router.delete("/preferences/{pref_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RequireFeature("notifications"))])
async def delete_preference(
    pref_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pref = await _get_preference(pref_id, db, current_user)
    await _block_retired_channel(
        db,
        channel=pref.channel,
        event_name="preference_delete_blocked",
        tenant_id=current_user.tenant_id,
    )
    await db.delete(pref)
    await db.commit()


@router.get("/notifications", dependencies=[Depends(RequireFeature("notifications"))])
async def list_notifications(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Recent notification history for the current user's tenant."""
    tenant = await db.get(Tenant, current_user.tenant_id)
    allowed_event_types = {"new_rfq", "daily_summary"}
    if tenant and tenant_has_feature(tenant, "intent_scoring"):
        allowed_event_types.update({"hot_visitor", "churn_risk"})
    if tenant and tenant_has_feature(tenant, "chat_handoff"):
        allowed_event_types.add("chat_handoff")
    if tenant and tenant_has_feature(tenant, "full_tracking"):
        allowed_event_types.add("content_suggestion")
    result = await db.exec(
        select(NotificationLog)
        .where(NotificationLog.tenant_id == current_user.tenant_id)
        .where(NotificationLog.event_type.in_(allowed_event_types))
        .order_by(NotificationLog.sent_at.desc())
        .limit(100)
    )
    logs = result.all()
    return {
        "data": [
            {
                "id": str(log.id),
                "channel": log.channel,
                "event_type": log.event_type,
                "event_ref_id": str(log.event_ref_id) if log.event_ref_id else None,
                "message_preview": log.message_preview,
                "status": log.status,
                "sent_at": log.sent_at.isoformat(),
            }
            for log in logs
        ]
    }


# ── Telegram Binding ──────────────────────────────────────────────────────────

@router.post("/telegram/bind-start", dependencies=[Depends(RequireFeature("notifications"))])
async def telegram_bind_start(
    body: TelegramBindStart,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Record attempted use while the Telegram entry is disabled."""
    await _block_retired_channel(
        db,
        channel="telegram",
        event_name="binding_start_blocked",
        tenant_id=current_user.tenant_id,
    )


@router.post("/telegram/bind-verify", dependencies=[Depends(RequireFeature("notifications"))])
async def telegram_bind_verify(
    body: TelegramBindVerify,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Record attempted use while the Telegram entry is disabled."""
    await _block_retired_channel(
        db,
        channel="telegram",
        event_name="binding_verify_blocked",
        tenant_id=current_user.tenant_id,
    )


# ── Telegram Incoming Webhook (public) ───────────────────────────────────────

@router.post("/webhook/telegram", include_in_schema=False)
async def telegram_webhook(
    db: AsyncSession = Depends(get_session),
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """
    Validate the provider secret, record PII-free use, and perform no processing
    while the channel is in retirement observation.
    """
    if not _telegram.verify_webhook_secret(x_telegram_bot_api_secret_token or ""):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    await record_retirement_usage(
        db,
        candidate_key="notification_telegram",
        event_name="verified_webhook_blocked",
        tenant_id=None,
        source="webhook",
    )
    return {"ok": True}


async def _process_copilot_message(
    chat_id: str,
    text: str,
    tenant_id: Optional[uuid.UUID],
    user_id: Optional[uuid.UUID],
) -> None:
    """
    Background task: sends typing indicator, runs the LLM engine, sends reply.
    Handles chunked responses (Telegram 4096-char limit).
    """
    from app.services.copilot.chat_engine import CopilotEngine

    # Show typing indicator immediately
    await _send_typing(chat_id)

    if not tenant_id:
        await _telegram.send({"chat_id": chat_id}, "⚠️ 找不到綁定的租戶資訊，請聯絡管理員。")
        return

    try:
        engine = CopilotEngine(
            tenant_id=tenant_id,
            user_id=user_id,
            channel="telegram",
            channel_user_id=chat_id,
        )
        chunks = await engine.run(text)
    except Exception as exc:
        logger.error("Copilot engine error (chat_id=%s): %s", chat_id, exc, exc_info=True)
        chunks = ["抱歉，AI 助理暫時無法回應，請稍後再試。"]

    # Send each chunk; show typing between chunks for long responses
    for i, chunk in enumerate(chunks):
        if i > 0:
            await _send_typing(chat_id)
        await _telegram.send({"chat_id": chat_id}, chunk)


async def _send_typing(chat_id: str) -> None:
    """Send 'typing...' action to Telegram — shows the animated indicator."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{token}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
    except Exception:
        pass  # Typing indicator is best-effort


# ── Web Chat ───────────────────────────────────────────────────────────────────

class WebChatIn(BaseModel):
    message: str


@router.post("/chat", dependencies=[Depends(RequireFeature("ai_copilot"))])
async def web_chat(
    body: WebChatIn,
    current_user: User = Depends(get_current_user),
):
    """
    Web chat endpoint — authenticated users can talk to the AI copilot directly
    from the admin dashboard without needing Telegram.
    Conversation history is keyed by (channel='web', channel_user_id=user_id).
    """
    from app.services.copilot.chat_engine import CopilotEngine

    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="訊息不可為空")
    if len(message) > 4000:
        raise HTTPException(status_code=400, detail="訊息長度不可超過 4000 字元")

    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="找不到租戶資訊")

    engine = CopilotEngine(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        channel="web",
        channel_user_id=str(current_user.id),
    )
    chunks = await engine.run(message)
    # For web we return all chunks joined — no Telegram limit applies
    reply = "\n\n".join(chunks)
    return {"reply": reply}


@router.get("/chat/history", dependencies=[Depends(RequireFeature("ai_copilot"))])
async def web_chat_history(
    limit: int = 40,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Return recent web-channel conversation history for the current user.
    Returned in chronological order (oldest first), skipping tool messages.
    """
    from sqlmodel import col

    from app.models.copilot_conversation import CopilotConversation

    limit = min(max(limit, 1), 100)
    result = await db.exec(
        select(CopilotConversation)
        .where(CopilotConversation.channel == "web")
        .where(CopilotConversation.channel_user_id == str(current_user.id))
        .where(CopilotConversation.role.in_(["user", "assistant"]))
        .order_by(col(CopilotConversation.created_at).desc())
        .limit(limit)
    )
    rows = list(reversed(result.all()))
    return {
        "data": [
            {
                "id": str(r.id),
                "role": r.role,
                "content": r.content,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    }


@router.delete("/chat/history", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RequireFeature("ai_copilot"))])
async def clear_web_chat_history(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Clear all web-channel conversation history for the current user."""
    from sqlmodel import delete

    from app.models.copilot_conversation import CopilotConversation

    await db.exec(
        delete(CopilotConversation)
        .where(CopilotConversation.channel == "web")
        .where(CopilotConversation.channel_user_id == str(current_user.id))
    )
    await db.commit()


# ── Observability ─────────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(RequireFeature("ai_copilot"))])
async def get_copilot_stats(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Return aggregate Copilot KPIs for the past 7 days scoped to the current tenant.

    Fields:
    - period: always "7d"
    - total_runs: total AI invocations
    - tool_hit_rate: % of runs that called at least one DB tool
    - error_rate: % of runs that returned a fallback/error reply
    - avg_duration_ms: mean wall-clock time per run
    - top_tools: [{name, count}] top-5 most-called tools
    """
    from app.models.copilot_run_log import CopilotRunLog

    since = utcnow_naive() - timedelta(days=7)
    result = await db.exec(
        select(CopilotRunLog)
        .where(CopilotRunLog.tenant_id == current_user.tenant_id)
        .where(CopilotRunLog.created_at >= since)
    )
    logs = result.all()

    total = len(logs)
    if total == 0:
        return {
            "period": "7d",
            "total_runs": 0,
            "tool_hit_rate": 0.0,
            "error_rate": 0.0,
            "avg_duration_ms": 0,
            "top_tools": [],
        }

    with_tools = sum(1 for r in logs if r.tool_count > 0)
    errors = sum(1 for r in logs if r.had_error)
    avg_ms = sum(r.duration_ms for r in logs) // total

    tool_counts: dict[str, int] = {}
    for r in logs:
        if r.tool_names:
            import json as _json
            for name in _json.loads(r.tool_names):
                tool_counts[name] = tool_counts.get(name, 0) + 1
    top_tools = sorted(
        [{"name": k, "count": v} for k, v in tool_counts.items()],
        key=lambda x: -x["count"],
    )[:5]

    return {
        "period": "7d",
        "total_runs": total,
        "tool_hit_rate": round(with_tools / total * 100, 1),
        "error_rate": round(errors / total * 100, 1),
        "avg_duration_ms": avg_ms,
        "top_tools": top_tools,
    }
