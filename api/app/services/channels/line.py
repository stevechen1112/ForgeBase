"""
LINE channel — sends notifications via LINE Messaging API (push message).

Config:
    LINE_CHANNEL_ACCESS_TOKEN — from LINE Developers console

Usage:
    channel = LineChannel()
    await channel.send({"line_user_id": "Uxxxx"}, "Hello!")
"""
import logging
import os
from typing import Optional

import httpx

from app.services.channels.base import BaseChannel

logger = logging.getLogger(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
_PUSH_API = "https://api.line.me/v2/bot/message/push"


class LineChannel(BaseChannel):
    """LINE Messaging API notification channel."""

    def channel_name(self) -> str:
        return "line"

    async def send(
        self,
        recipient_config: dict,
        message: str,
        buttons: Optional[list[dict]] = None,
    ) -> bool:
        """
        Send a LINE push message.

        recipient_config: {"line_user_id": "Uxxxxxxxx"}
        buttons: [{"label": "查看後台", "url": "https://..."}]
                 → rendered as a URI action template (max 4 per LINE spec)
        """
        if not LINE_CHANNEL_ACCESS_TOKEN:
            logger.debug("LINE_CHANNEL_ACCESS_TOKEN not configured — skipping")
            return False

        to = recipient_config.get("line_user_id") or recipient_config.get("user_id")
        if not to:
            logger.warning("LineChannel.send: missing line_user_id in recipient_config")
            return False

        url_buttons = [b for b in (buttons or []) if b.get("url")][:4]
        if url_buttons:
            line_message = {
                "type": "template",
                "altText": message[:400],
                "template": {
                    "type": "buttons",
                    "text": message[:160],
                    "actions": [
                        {"type": "uri", "label": btn["label"][:20], "uri": btn["url"]}
                        for btn in url_buttons
                    ],
                },
            }
        else:
            # LINE text messages cap at 5000 chars
            line_message = {"type": "text", "text": message[:5000]}

        payload = {"to": to, "messages": [line_message]}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    _PUSH_API,
                    json=payload,
                    headers={"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"},
                )
                if resp.status_code == 200:
                    return True
                logger.warning(
                    "LINE push failed: %s %s", resp.status_code, resp.text[:200]
                )
                return False
        except Exception as exc:
            logger.error("LINE send error: %s", exc)
            return False
