"""
Copilot API — Notification preferences CRUD + Telegram webhook receiver.

Endpoints:
  GET    /copilot/preferences          — list user's notification preferences
  POST   /copilot/preferences          — create a preference row
  PUT    /copilot/preferences/{id}     — update toggles / quiet hours
  DELETE /copilot/preferences/{id}     — remove a channel preference
  GET    /copilot/notifications        — notification history (last 100)
  POST   /copilot/telegram/bind-start  — generate binding code + send to Telegram
  POST   /copilot/telegram/bind-verify — verify code and save chat_id
  POST   /copilot/webhook/telegram     — Telegram Bot webhook receiver (public)
"""
import asyncio
import json
import logging
import random
import string
import uuid
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.notification_preference import NotificationPreference
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.services.channels.telegram import TelegramChannel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/copilot", tags=["Copilot"])
_telegram = TelegramChannel()

_BINDING_CODE_EXPIRY_MINUTES = 10
_VALID_CHANNELS = {"telegram", "email", "in_app"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class PreferenceIn(BaseModel):
    channel: str
    channel_config: dict = {}
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

def _generate_code(length: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/preferences")
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
                "created_at": p.created_at.isoformat(),
            }
            for p in prefs
        ]
    }


@router.post("/preferences", status_code=status.HTTP_201_CREATED)
async def create_preference(
    body: PreferenceIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if body.channel not in _VALID_CHANNELS:
        raise HTTPException(status_code=400, detail=f"Invalid channel. Allowed: {_VALID_CHANNELS}")

    pref = NotificationPreference(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        channel=body.channel,
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


@router.put("/preferences/{pref_id}")
async def update_preference(
    pref_id: uuid.UUID,
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pref = await _get_preference(pref_id, db, current_user)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(pref, field, value)
    pref.updated_at = utcnow_naive()
    db.add(pref)
    await db.commit()
    return {"ok": True}


@router.delete("/preferences/{pref_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(
    pref_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pref = await _get_preference(pref_id, db, current_user)
    await db.delete(pref)
    await db.commit()


@router.get("/notifications")
async def list_notifications(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Recent notification history for the current user's tenant."""
    result = await db.exec(
        select(NotificationLog)
        .where(NotificationLog.tenant_id == current_user.tenant_id)
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

@router.post("/telegram/bind-start")
async def telegram_bind_start(
    body: TelegramBindStart,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Step 1: Admin provides their Telegram chat_id.
    We generate a time-limited code and send it via the bot.
    """
    # Find or create a telegram preference row (pending binding)
    result = await db.exec(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == current_user.id)
        .where(NotificationPreference.channel == "telegram")
    )
    pref = result.first()

    code = _generate_code(6)
    expires_at = utcnow_naive() + timedelta(minutes=_BINDING_CODE_EXPIRY_MINUTES)

    if pref:
        pref.binding_code = code
        pref.binding_code_expires_at = expires_at
        pref.updated_at = utcnow_naive()
    else:
        pref = NotificationPreference(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            channel="telegram",
            channel_config=json.dumps({"chat_id": body.telegram_chat_id}),
            enabled=False,  # not active until verified
            binding_code=code,
            binding_code_expires_at=expires_at,
        )

    db.add(pref)
    await db.commit()

    # Send verification code via Telegram Bot
    sent = await _telegram.send_binding_code(body.telegram_chat_id, code)
    if not sent:
        raise HTTPException(
            status_code=502,
            detail="無法發送 Telegram 驗證碼，請確認 Bot Token 是否設定，以及 chat_id 是否正確",
        )

    return {"message": f"驗證碼已發送至 Telegram，請在 {_BINDING_CODE_EXPIRY_MINUTES} 分鐘內完成驗證"}


@router.post("/telegram/bind-verify")
async def telegram_bind_verify(
    body: TelegramBindVerify,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Step 2: Admin enters the 6-char code received on Telegram.
    If valid, the preference becomes enabled.
    """
    result = await db.exec(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == current_user.id)
        .where(NotificationPreference.channel == "telegram")
        .where(NotificationPreference.binding_code == body.code.upper())
    )
    pref = result.first()

    if not pref:
        raise HTTPException(status_code=400, detail="驗證碼不正確")
    if pref.binding_code_expires_at and utcnow_naive() > pref.binding_code_expires_at:
        raise HTTPException(status_code=400, detail="驗證碼已過期，請重新發送")

    pref.enabled = True
    pref.binding_code = None
    pref.binding_code_expires_at = None
    pref.updated_at = utcnow_naive()
    db.add(pref)
    await db.commit()

    return {"message": "Telegram 通知綁定成功！"}


# ── Telegram Incoming Webhook (public) ───────────────────────────────────────

@router.post("/webhook/telegram", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_session),
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """
    Receives incoming messages from Telegram (set via setWebhook).
    Validated by HMAC secret — intentionally unauthenticated.
    Routes to full LLM Copilot engine with persistent conversation history.
    Returns 200 immediately; reply is sent asynchronously.
    """
    if not _telegram.verify_webhook_secret(x_telegram_bot_api_secret_token or ""):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    body = await request.json()
    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}  # Telegram expects 200

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return {"ok": True}

    # Find bound preference for this chat_id
    result = await db.exec(
        select(NotificationPreference)
        .where(NotificationPreference.channel == "telegram")
        .where(NotificationPreference.channel_config.contains(chat_id))
        .where(NotificationPreference.enabled == True)
    )
    pref = result.first()

    if not pref:
        await _telegram.send(
            {"chat_id": chat_id},
            "⚠️ 此 Telegram 帳號尚未綁定 ForgeBase。\n請至後台 <b>通知設定</b> 頁面完成 Telegram 綁定。",
        )
        return {"ok": True}

    # Fire and forget — process in background so Telegram doesn't timeout
    background_tasks.add_task(
        _process_copilot_message,
        chat_id=chat_id,
        text=text,
        tenant_id=pref.tenant_id,
        user_id=pref.user_id,
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
