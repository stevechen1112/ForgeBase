"""Auto-Acknowledge：RFQ 自動專業確認信（T6）。

設計依據：FORGEBASE_LEADS_EFFECTIVENESS_PLAN.md §5.3「首回速度工程」。
買家同時評估多家供應商，先給出專業確認者先進 shortlist。
Per-tenant 開關（ops_config.auto_reply_enabled，預設關）；
低品質／垃圾單不發（門檻 AUTO_REPLY_MIN_QUALITY）。
發送時間對齊買家上班時段：非工作時間送進來的單，由 durable
operational outbox 延後到可寄送時間，不阻塞 worker，也不因重啟遺失。
"""
import html
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.services.sla import add_business_hours, load_sla_hours, timezone_for_country

logger = logging.getLogger(__name__)

AUTO_REPLY_MIN_QUALITY = 30
_MAX_DEFER_SECONDS = 12 * 3600  # 最多延後 12 小時


class AutoReplyDeferred(Exception):
    """Signal the durable worker to reschedule without blocking its event loop."""

    def __init__(self, delay_seconds: float):
        self.delay_seconds = max(1.0, delay_seconds)
        super().__init__(f"Auto reply deferred for {self.delay_seconds:.0f} seconds")


def _esc(value: Optional[str]) -> str:
    return html.escape(value or "", quote=True)


def build_ack_email(
    *,
    rfq_number: str,
    form: dict,
    missing_info: list[str],
    sla_hours: float,
    signature: str,
    company_display: str,
) -> tuple[str, str]:
    """產生專業英文確認信（subject, html_body）。純函式，便於測試。"""
    full_name = form.get("full_name") or "there"
    specs = (form.get("specifications") or "").strip()
    quantity = (form.get("quantity") or "").strip()

    subject = f"Re: Your RFQ {rfq_number} — received and under review"

    requirement_lines = ""
    if quantity or specs:
        requirement_lines += "<p><b>Your requirements as we understand them:</b></p><ul>"
        if quantity:
            requirement_lines += f"<li>Quantity: {_esc(quantity)}</li>"
        if specs:
            requirement_lines += f"<li>Specifications: {_esc(specs[:300])}</li>"
        requirement_lines += "</ul>"

    missing_block = ""
    if missing_info:
        items = "".join(f"<li>{_esc(item)}</li>" for item in missing_info)
        missing_block = (
            "<p>To prepare an accurate quotation, it would help if you could also share:</p>"
            f"<ul>{items}</ul>"
        )

    sla_text = f"{int(sla_hours)}" if float(sla_hours).is_integer() else f"{sla_hours:.1f}"
    signature_html = html.escape(signature, quote=False).replace("\n", "<br>")

    body = f"""
<p>Dear {_esc(full_name)},</p>

<p>Thank you for your inquiry (<b>{_esc(rfq_number)}</b>) — we have received
your request and our sales engineering team is already reviewing it.</p>

{requirement_lines}
{missing_block}
<p>You can expect a detailed quotation from us <b>within {sla_text} business hours</b>
of your local working day. If anything is urgent, simply reply to
this email and it will reach the responsible account manager directly.</p>

<p>Best regards,<br>
{signature_html}<br>
{_esc(company_display)}</p>
""".strip()
    return subject, body


def compute_missing_info(form: dict) -> list[str]:
    """依 T10 貿易欄位缺口產生「還缺哪些資訊」清單（英文、給買家看）。"""
    missing: list[str] = []
    if not (form.get("quantity") or "").strip():
        missing.append("Estimated order quantity or annual volume")
    if not (form.get("specifications") or "").strip():
        missing.append("Technical specifications or drawings (material, tolerances, standards)")
    if not form.get("incoterm"):
        missing.append("Preferred trade terms (e.g. FOB, CIF, DAP) and destination port")
    if not form.get("required_certs"):
        missing.append("Required certifications for your market (e.g. CE, FDA, UL, RoHS)")
    if not (form.get("timeline") or "").strip():
        missing.append("Target delivery schedule")
    return missing[:4]  # 最多列四項，避免嚇到買家


def seconds_until_business_open(tz_name: str, now: Optional[datetime] = None) -> float:
    """距離買家下一個上班時段開頭的秒數；已在上班時段內回 0。"""
    now = now or utcnow_naive()
    next_open = add_business_hours(now, 0, tz_name)
    return max(0.0, (next_open - now).total_seconds())


async def maybe_auto_reply(rfq_id: uuid.UUID, tenant_id: Optional[uuid.UUID]) -> bool:
    """RFQ 建立後由 submit_rfq 非同步觸發。回傳是否實際寄出。"""
    from sqlmodel import select

    from app.models.contact import Contact
    from app.models.rfq_event import RFQEvent
    from app.models.rfq_request import RFQRequest
    from app.services.email_service import send_email_result
    from app.services.ops_config import load_ops_config

    async with get_session_ctx() as db:
        config = await load_ops_config(tenant_id, db)
        if not config.get("auto_reply_enabled"):
            return False

        rfq = await db.get(RFQRequest, rfq_id)
        if not rfq:
            return False
        if (rfq.quality_score or 0) < AUTO_REPLY_MIN_QUALITY:
            logger.info("auto-reply skipped (quality=%s) for %s", rfq.quality_score, rfq.rfq_number)
            return False

        form = json.loads(rfq.form_data) if rfq.form_data else {}
        contact = await db.get(Contact, rfq.contact_id) if rfq.contact_id else None
        recipient = (contact.email if contact else None) or form.get("email")
        if not recipient:
            return False

        # 冪等：已發過就不再發（例如重試或重觸發）
        already = (
            await db.exec(
                select(RFQEvent).where(
                    RFQEvent.rfq_id == rfq_id,
                    RFQEvent.event_type == "auto_reply_sent",
                )
            )
        ).first()
        if already:
            return False

        company_display = "ForgeBase"
        sla_hours = await load_sla_hours(tenant_id, db)
        tz_name = rfq.buyer_timezone or timezone_for_country(form.get("country"))
        signature = config.get("auto_reply_signature") or "Sales Team"
        from_name = config.get("auto_reply_from_name") or None

        missing = compute_missing_info(form)
        subject, body = build_ack_email(
            rfq_number=rfq.rfq_number,
            form=form,
            missing_info=missing,
            sla_hours=sla_hours,
            signature=signature,
            company_display=company_display,
        )

    # 對齊買家上班時段。交由 durable outbox 重排時間，不能在單一
    # worker 內 sleep 數小時，否則後續 RFQ 工作全部被阻塞。
    delay = min(seconds_until_business_open(tz_name), _MAX_DEFER_SECONDS)
    if delay > 1:
        raise AutoReplyDeferred(delay)

    delivery = await send_email_result(
        to=recipient,
        subject=subject,
        html_body=body,
        text_body=None,
        from_name=from_name,
        idempotency_key=f"rfq-auto-reply-{rfq_id}",
        recipient_kind="external",
    )
    if delivery.dry_run:
        logger.info("auto-reply simulated but not sent for %s", rfq.rfq_number)
        return False
    if not delivery.delivered:
        logger.warning("auto-reply send failed for %s", rfq.rfq_number)
        raise RuntimeError(f"Auto-reply delivery failed for {rfq.rfq_number}")

    async with get_session_ctx() as db:
        db.add(RFQEvent(
            rfq_id=rfq_id,
            event_type="auto_reply_sent",
            summary=f"Auto-acknowledge email sent to {recipient}",
            tenant_id=tenant_id,
            detail=json.dumps({
                "quality_score": rfq.quality_score,
                "tz": tz_name,
                "provider": delivery.provider,
                "provider_message_id": delivery.message_id,
            }),
        ))
        # 自動確認信也算首回（速度紅利）
        rfq_row = await db.get(RFQRequest, rfq_id)
        if rfq_row and rfq_row.first_response_at is None:
            rfq_row.first_response_at = utcnow_naive()
            db.add(rfq_row)
        await db.commit()
    return True
