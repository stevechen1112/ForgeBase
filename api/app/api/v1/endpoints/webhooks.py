from __future__ import annotations

import hashlib
import json
import logging
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.email_delivery import EmailDeliveryEvent, EmailSuppression
from app.models.outreach import OutreachMessage
from app.services.email_governance import email_hash, mask_email
from app.services.inbound_reply.runtime import ingest_resend_receipt
from app.services.outreach.delivery import cancel_queued_for_hash
from app.services.outreach.events import (
    apply_delivery_event,
    link_unknown_delivery_events,
)
from app.services.resend_webhook import (
    decode_payload,
    parse_occurred_at,
    provider_message_id,
    recipient_addresses,
    verify_resend_signature,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_SUPPRESSION_ADD_EVENTS = {
    "email.bounced",
    "email.complained",
    "email.suppressed",
    "suppression.added",
}
_SUPPRESSION_REMOVE_EVENTS = {"suppression.removed"}


def _should_add_suppression(event_type: str, payload: dict) -> bool:
    if event_type != "email.bounced":
        return event_type in _SUPPRESSION_ADD_EVENTS
    bounce = (payload.get("data") or {}).get("bounce") or {}
    bounce_type = str(bounce.get("type") or "").strip().lower()
    # Transient/soft bounces remain observable events but must not permanently
    # suppress a valid buyer address. Resend will separately emit
    # suppression.added when its own suppression list changes.
    return bounce_type in {"permanent", "hard", "hard_bounce"}


def _suppression_reason(event_type: str, payload: dict) -> str:
    data = payload.get("data") or {}
    if event_type == "email.bounced":
        bounce = data.get("bounce") or {}
        subtype = bounce.get("subType") or bounce.get("type")
        return f"bounce:{str(subtype or 'unknown').lower()}"[:50]
    if event_type == "email.complained":
        return "complaint"
    if event_type in {"email.suppressed", "suppression.added"}:
        return str(data.get("reason") or "provider_suppression")[:50]
    return event_type[:50]


def _safe_event_data(event_type: str, payload: dict) -> dict:
    data = payload.get("data") or {}
    if event_type == "email.clicked":
        link = (data.get("click") or {}).get("link") or data.get("link") or ""
        try:
            return {"click_domain": (urlparse(str(link)).hostname or "")[:253]}
        except ValueError:
            return {"click_domain": ""}
    if event_type == "email.bounced":
        bounce = data.get("bounce") or {}
        return {
            "bounce_type": str(bounce.get("type") or "unknown")[:50],
            "bounce_subtype": str(bounce.get("subType") or "")[:80],
        }
    if event_type in {"email.complained", "email.suppressed", "suppression.added"}:
        return {
            "reason": str(
                data.get("reason") or _suppression_reason(event_type, payload)
            )[:100]
        }
    return {}


@router.post("/resend", status_code=status.HTTP_202_ACCEPTED)
async def receive_resend_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    """Authenticated Resend webhook; raw recipient addresses are never stored."""
    content_length = request.headers.get("content-length")
    if (
        content_length
        and content_length.isdigit()
        and int(content_length) > settings.INBOUND_REPLY_MAX_WEBHOOK_BYTES
    ):
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    raw_body = await request.body()
    if len(raw_body) > settings.INBOUND_REPLY_MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload is too large")
    headers = {key.lower(): value for key, value in request.headers.items()}
    if not verify_resend_signature(raw_body, headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    try:
        payload = decode_payload(raw_body)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    event_id = headers["svix-id"][:120]
    event_type = str(payload.get("type") or "unknown")[:50]
    if event_type == "email.received":
        receipt, queued, created = await ingest_resend_receipt(
            db,
            payload=payload,
            provider_event_id=event_id,
            raw_payload_sha256=hashlib.sha256(raw_body).hexdigest(),
        )
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return {"accepted": True, "duplicate": True, "queued": False}
        return {
            "accepted": True,
            "duplicate": bool(receipt) and not created,
            "ignored": receipt is None,
            "queued": queued,
        }
    existing = (
        await db.exec(
            select(EmailDeliveryEvent.id).where(
                EmailDeliveryEvent.provider_event_id == event_id
            )
        )
    ).first()
    if existing:
        return {"accepted": True, "duplicate": True}

    addresses = recipient_addresses(payload)
    primary = addresses[0] if addresses else None
    message_id = provider_message_id(payload)
    recipient_digest = email_hash(primary) if primary else None
    message = None
    if message_id and recipient_digest:
        message = (
            await db.exec(
                select(OutreachMessage)
                .where(
                    OutreachMessage.provider == "resend",
                    OutreachMessage.provider_message_id == message_id,
                    OutreachMessage.to_email_hash == recipient_digest,
                )
                .with_for_update()
            )
        ).first()
    occurred_at = parse_occurred_at(payload) or utcnow_naive()
    delivery_event = EmailDeliveryEvent(
        provider_event_id=event_id,
        provider_message_id=message_id,
        event_type=event_type,
        recipient_hash=recipient_digest,
        recipient_masked=mask_email(primary) if primary else None,
        tenant_id=message.tenant_id if message else None,
        outreach_message_id=message.id if message else None,
        reason_code=_suppression_reason(event_type, payload)
        if event_type in _SUPPRESSION_ADD_EVENTS
        else None,
        event_data_json=json.dumps(
            _safe_event_data(event_type, payload), separators=(",", ":")
        ),
        is_unknown_message=message is None,
        occurred_at=occurred_at,
    )
    db.add(delivery_event)
    if message:
        apply_delivery_event(message, event_type, occurred_at)
        db.add(message)

    changed = 0
    if (
        _should_add_suppression(event_type, payload)
        or event_type in _SUPPRESSION_REMOVE_EVENTS
    ):
        active = _should_add_suppression(event_type, payload)
        reason = _suppression_reason(event_type, payload)
        now = utcnow_naive()
        for address in addresses:
            digest = email_hash(address)
            row = (
                await db.exec(
                    select(EmailSuppression).where(
                        EmailSuppression.scope_key == "global",
                        EmailSuppression.email_hash == digest,
                    )
                )
            ).first()
            if row:
                row.active = active
                row.reason = reason
                row.source_event_id = event_id
                row.updated_at = now
            else:
                row = EmailSuppression(
                    email_hash=digest,
                    email_masked=mask_email(address),
                    reason=reason,
                    source_event_id=event_id,
                    active=active,
                )
            db.add(row)
            changed += 1
            if active:
                await cancel_queued_for_hash(
                    db,
                    email_digest=digest,
                    tenant_id=None,
                    reason=f"Provider event: {reason}",
                )
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent retry: the unique provider event id remains the final
        # replay-protection boundary.
        await db.rollback()
        return {"accepted": True, "duplicate": True}
    if message is None and message_id and recipient_digest:
        # Mirror the provider-response post-commit check. In every commit
        # ordering, the side that commits last can link an early event.
        late_message = (
            await db.exec(
                select(OutreachMessage)
                .where(
                    OutreachMessage.provider == "resend",
                    OutreachMessage.provider_message_id == message_id,
                    OutreachMessage.to_email_hash == recipient_digest,
                )
                .with_for_update()
            )
        ).first()
        if late_message:
            await link_unknown_delivery_events(db, late_message)
            db.add(late_message)
            await db.commit()
    logger.info(
        "Resend webhook accepted event_type=%s suppressions_changed=%s",
        event_type,
        changed,
    )
    return {"accepted": True, "duplicate": False, "suppressions_changed": changed}
