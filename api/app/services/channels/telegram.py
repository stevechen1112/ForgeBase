"""
Telegram channel — sends notifications via Telegram Bot API.

Config:
    TELEGRAM_BOT_TOKEN  — from @BotFather
    TELEGRAM_WEBHOOK_SECRET — used to verify incoming webhook requests

Usage:
    channel = TelegramChannel()
    await channel.send({"chat_id": "123456"}, "Hello!")
"""
import hashlib
import hmac
import logging
import os
from typing import Optional

import httpx

from app.services.channels.base import BaseChannel

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_SECRET = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
_BOT_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class TelegramChannel(BaseChannel):
    """Telegram Bot API notification channel."""

    def channel_name(self) -> str:
        return "telegram"

    async def send(
        self,
        recipient_config: dict,
        message: str,
        buttons: Optional[list[dict]] = None,
    ) -> bool:
        """
        Send a Telegram message.

        recipient_config: {"chat_id": "123456789"}
        buttons: [{"label": "查看後台", "url": "https://..."}]
                 → rendered as inline keyboard URL buttons
        """
        if not TELEGRAM_BOT_TOKEN:
            logger.debug("TELEGRAM_BOT_TOKEN not configured — skipping")
            return False

        chat_id = recipient_config.get("chat_id")
        if not chat_id:
            logger.warning("TelegramChannel.send: missing chat_id in recipient_config")
            return False

        payload: dict = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        if buttons:
            inline_keyboard = [
                [{"text": btn["label"], "url": btn["url"]}]
                for btn in buttons
                if btn.get("url")
            ]
            if inline_keyboard:
                payload["reply_markup"] = {"inline_keyboard": inline_keyboard}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{_BOT_API}/sendMessage", json=payload)
                if resp.status_code == 200:
                    return True
                logger.warning(
                    "Telegram sendMessage failed: %s %s", resp.status_code, resp.text[:200]
                )
                return False
        except Exception as exc:
            logger.error("Telegram send error: %s", exc)
            return False

    async def set_webhook(self, webhook_url: str) -> bool:
        """Register a webhook URL with Telegram."""
        if not TELEGRAM_BOT_TOKEN:
            return False
        payload: dict = {"url": webhook_url}
        if TELEGRAM_WEBHOOK_SECRET:
            payload["secret_token"] = TELEGRAM_WEBHOOK_SECRET
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(f"{_BOT_API}/setWebhook", json=payload)
                return resp.status_code == 200
        except Exception as exc:
            logger.error("Telegram setWebhook error: %s", exc)
            return False

    def verify_webhook_secret(self, token: str) -> bool:
        """Validate X-Telegram-Bot-Api-Secret-Token header."""
        if not TELEGRAM_WEBHOOK_SECRET:
            from app.core.config import settings
            if settings.is_production:
                logger.error("TELEGRAM_WEBHOOK_SECRET not set in production — rejecting webhook")
                return False
            logger.warning("TELEGRAM_WEBHOOK_SECRET not set — skipping verification (dev only)")
            return True
        return hmac.compare_digest(token or "", TELEGRAM_WEBHOOK_SECRET)

    async def send_binding_code(self, chat_id: str, code: str) -> bool:
        """Send a pairing verification code to a Telegram user."""
        msg = (
            f"🔐 <b>ForgeBase 綁定驗證碼</b>\n\n"
            f"您的驗證碼：<code>{code}</code>\n\n"
            f"請在後台輸入此碼完成 Telegram 通知綁定。\n"
            f"驗證碼 10 分鐘內有效。"
        )
        return await self.send({"chat_id": chat_id}, msg)
