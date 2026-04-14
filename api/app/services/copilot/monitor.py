"""
AI Copilot — Event Monitor

Triggered by API-layer hooks (RFQ creation, visitor stage change, chat handoff, score decay).
Decides whether to fire a notification and formats the message.

Public API:
    await on_new_rfq(rfq_id, tenant_id)
    await on_hot_visitor(visitor_id, tenant_id)
    await on_chat_handoff(session_id, tenant_id)
    await on_churn_risk(visitor_id, tenant_id)
"""
import json
import logging
import uuid
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.db.session import get_session_ctx
from app.models.rfq_request import RFQRequest
from app.models.visitor import Visitor
from app.models.contact import Contact
from app.models.chat import ChatSession
from app.services.notification_router import send_notification

logger = logging.getLogger(__name__)

_ADMIN_URL = settings.ADMIN_URL.rstrip("/")


# ── RFQ stage urgency ──────────────────────────────────────────────────────────

_URGENCY_ICON = {
    "urgent": "🔴",
    "high": "🟠",
    "normal": "🟢",
}

_STAGE_ICON = {
    "sales_ready": "🔥",
    "hot": "⚡",
    "warm": "🌡",
    "cold": "❄️",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_form_data(raw: Optional[str]) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


async def _get_rfq(session: AsyncSession, rfq_id: uuid.UUID) -> Optional[RFQRequest]:
    result = await session.exec(select(RFQRequest).where(RFQRequest.id == rfq_id))
    return result.first()


async def _get_visitor(session: AsyncSession, visitor_id: uuid.UUID) -> Optional[Visitor]:
    result = await session.exec(select(Visitor).where(Visitor.visitor_id == visitor_id))
    return result.first()


async def _get_contact(session: AsyncSession, contact_id: uuid.UUID) -> Optional[Contact]:
    result = await session.exec(select(Contact).where(Contact.id == contact_id))
    return result.first()


async def _ai_rfq_summary(rfq: RFQRequest) -> str:
    """Call AI RFQ analysis and return a compact summary string."""
    try:
        from app.services.ai_rfq import analyze_rfq
        form = _parse_form_data(rfq.form_data)
        result = await analyze_rfq(
            rfq_data=form,
            products=[],  # minimal call — no catalog needed for summary
        )
        return result.get("summary", "（AI 摘要不可用）")
    except Exception as exc:
        logger.warning("AI RFQ summary failed: %s", exc)
        return "（AI 分析暫時不可用）"


# ── Event handlers ────────────────────────────────────────────────────────────

async def on_new_rfq(rfq_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    """
    Triggered when a new RFQ is created.
    Sends an immediate notification with AI-generated summary.
    """
    async with get_session_ctx() as session:
        rfq = await _get_rfq(session, rfq_id)
        if not rfq:
            return

        form = _parse_form_data(rfq.form_data)
        company = form.get("company_name") or form.get("company") or "—"
        full_name = form.get("full_name") or form.get("name") or "—"
        email = form.get("email") or "—"
        quantity = form.get("quantity") or "—"
        message_text = (form.get("message") or "")[:120]

        urgency_icon = _URGENCY_ICON.get(rfq.priority or "normal", "🟢")
        score = rfq.intent_score_at_submit or 0

        # Async AI summary (with fallback)
        ai_summary = await _ai_rfq_summary(rfq)

        msg = (
            f"🔔 <b>新 RFQ 詢價通知</b>\n\n"
            f"編號：<code>{rfq.rfq_number}</code>\n"
            f"公司：{company}\n"
            f"聯絡人：{full_name}（{email}）\n"
            f"數量：{quantity}\n"
            f"意圖分數：{score} {urgency_icon}\n"
        )
        if message_text:
            msg += f"\n訊息：{message_text}{'…' if len(form.get('message',''))>120 else ''}\n"
        msg += f"\n<b>AI 摘要：</b>{ai_summary}"

        buttons = [
            {"label": "查看 RFQ 詳情", "url": f"{_ADMIN_URL}/backend/rfq/{rfq_id}"},
        ]

    await send_notification(
        tenant_id=tenant_id,
        event_type="new_rfq",
        event_ref_id=rfq_id,
        message=msg,
        buttons=buttons,
    )


async def on_hot_visitor(visitor_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    """
    Triggered when a visitor's intent stage upgrades to hot or sales_ready.
    """
    async with get_session_ctx() as session:
        visitor = await _get_visitor(session, visitor_id)
        if not visitor:
            return

        stage = visitor.intent_stage
        score = visitor.intent_score
        stage_icon = _STAGE_ICON.get(stage, "⚡")
        country = visitor.country or "—"
        pages = visitor.total_page_views

        contact_info = ""
        if visitor.contact_id:
            contact = await _get_contact(session, visitor.contact_id)
            if contact:
                name = contact.full_name or "—"
                company = contact.company_name or "—"
                email = contact.email or "—"
                contact_info = f"身份：{name} / {company}（{email}）\n"

    msg = (
        f"{stage_icon} <b>高意圖訪客偵測</b>\n\n"
        f"Stage：<b>{stage}</b>（分數 {score}）\n"
        f"{contact_info}"
        f"來源國：{country}\n"
        f"瀏覽頁數：{pages}\n\n"
        f"建議立即透過 Email 或 Chat 主動接觸，搶在訪客失溫前推進對話。"
    )

    buttons = [
        {"label": "查看訪客詳情", "url": f"{_ADMIN_URL}/backend/visitors/{visitor_id}"},
    ]

    await send_notification(
        tenant_id=tenant_id,
        event_type="hot_visitor",
        event_ref_id=visitor_id,
        message=msg,
        buttons=buttons,
    )


async def on_chat_handoff(session_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    """
    Triggered when AI chat advisor escalates to human handoff.
    """
    async with get_session_ctx() as session:
        result = await session.exec(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        chat = result.first()
        if not chat:
            return

        visitor_id = chat.visitor_id
        context_type = chat.context_entity_type or "未知頁面"
        msg_count = chat.message_count

        visitor_info = ""
        if visitor_id:
            v = await _get_visitor(session, visitor_id)
            if v and v.contact_id:
                c = await _get_contact(session, v.contact_id)
                if c:
                    visitor_info = f"訪客身份：{c.full_name or '—'} / {c.company_name or '—'}\n"

    msg = (
        f"💬 <b>Chat 訪客請求人工接手</b>\n\n"
        f"{visitor_info}"
        f"對話頁面：{context_type}\n"
        f"已訊息數：{msg_count} 則\n\n"
        f"請盡快登入後台接續對話，避免訪客等待過久。"
    )

    buttons = [
        {"label": "查看對話記錄", "url": f"{_ADMIN_URL}/backend/chat/{session_id}"},
    ]

    await send_notification(
        tenant_id=tenant_id,
        event_type="chat_handoff",
        event_ref_id=session_id,
        message=msg,
        buttons=buttons,
    )


async def on_churn_risk(visitor_id: uuid.UUID, tenant_id: uuid.UUID, old_stage: str) -> None:
    """
    Triggered by score_decay when a visitor's stage downgrades.
    Only fires if visitor has a known contact (identified).
    """
    async with get_session_ctx() as session:
        visitor = await _get_visitor(session, visitor_id)
        if not visitor or not visitor.contact_id:
            # Anonymous visitors: skip (not actionable)
            return

        contact = await _get_contact(session, visitor.contact_id)
        if not contact:
            return

        new_stage = visitor.intent_stage
        name = contact.full_name or "訪客"
        company = contact.company_name or "—"
        email = contact.email or "—"
        days_inactive = 0
        if visitor.last_activity_at:
            from app.core.datetime import utcnow_naive
            delta = utcnow_naive() - visitor.last_activity_at
            days_inactive = delta.days

    msg = (
        f"⚠️ <b>客戶流失風險警報</b>\n\n"
        f"聯絡人：{name}（{company}）\n"
        f"Email：{email}\n"
        f"Stage 變化：{old_stage} → <b>{new_stage}</b>\n"
        f"最後活動：{days_inactive} 天前\n\n"
        f"建議發送 Re-engagement Email，或直接由業務主動聯繫。"
    )

    buttons = [
        {"label": "查看聯絡人", "url": f"{_ADMIN_URL}/backend/contacts/{contact.id}"},
    ]

    await send_notification(
        tenant_id=tenant_id,
        event_type="churn_risk",
        event_ref_id=visitor_id,
        message=msg,
        buttons=buttons,
    )
