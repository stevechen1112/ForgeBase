"""Monotonic outreach delivery-state projection."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import select

from app.core.datetime import utcnow_naive
from app.models.email_delivery import EmailDeliveryEvent
from app.models.outreach import OutreachMessage

_EVENT_STATUS = {
    "email.sent": "sent",
    "email.delivered": "delivered",
    "email.opened": "opened",
    "email.clicked": "clicked",
    "email.bounced": "bounced",
    "email.complained": "complained",
    "email.unsubscribed": "unsubscribed",
}
_RANK = {
    "draft": 0,
    "pending_review": 0,
    "approved": 0,
    "queued": 1,
    "sending": 2,
    "sent": 3,
    "delivered": 4,
    "opened": 5,
    "clicked": 6,
    "replied": 7,
    # Provider events are stronger evidence than an exhausted internal retry.
    "failed": 2,
    "cancelled": 8,
    "bounced": 10,
    "complained": 11,
    "unsubscribed": 12,
}
_TIMESTAMP_FIELD = {
    "email.sent": "sent_at",
    "email.delivered": "delivered_at",
    "email.opened": "opened_at",
    "email.clicked": "clicked_at",
    "email.bounced": "bounced_at",
    "email.complained": "complained_at",
    "email.unsubscribed": "unsubscribed_at",
}


def apply_delivery_event(
    message: OutreachMessage, event_type: str, occurred_at: datetime
) -> None:
    changed = False
    field = _TIMESTAMP_FIELD.get(event_type)
    if field:
        existing = getattr(message, field)
        if existing is None or occurred_at < existing:
            setattr(message, field, occurred_at)
            changed = True
    status = _EVENT_STATUS.get(event_type)
    if status and _RANK.get(status, 0) > _RANK.get(message.status, 0):
        message.status = status
        changed = True
    if changed:
        message.updated_at = utcnow_naive()


async def link_unknown_delivery_events(db, message: OutreachMessage) -> int:
    if not message.provider_message_id:
        return 0
    rows = list(
        (
            await db.exec(
                select(EmailDeliveryEvent).where(
                    EmailDeliveryEvent.provider == message.provider,
                    EmailDeliveryEvent.provider_message_id
                    == message.provider_message_id,
                    EmailDeliveryEvent.recipient_hash == message.to_email_hash,
                    EmailDeliveryEvent.is_unknown_message.is_(True),
                )
            )
        ).all()
    )
    for event in rows:
        event.tenant_id = message.tenant_id
        event.outreach_message_id = message.id
        event.is_unknown_message = False
        apply_delivery_event(
            message, event.event_type, event.occurred_at or event.created_at
        )
        db.add(event)
    return len(rows)
