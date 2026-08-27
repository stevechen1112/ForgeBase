from __future__ import annotations

import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.operational_job import OperationalJob
from app.services.operational_outbox import enqueue_operational_job

INBOUND_REPLY_FETCH_JOB_TYPE = "inbound_reply_fetch"


def enqueue_inbound_reply_fetch(
    db: AsyncSession, *, tenant_id: uuid.UUID, inbound_reply_id: uuid.UUID
) -> OperationalJob:
    return enqueue_operational_job(
        db,
        job_type=INBOUND_REPLY_FETCH_JOB_TYPE,
        tenant_id=tenant_id,
        payload={"inbound_reply_id": str(inbound_reply_id)},
        idempotency_key=f"inbound-reply-fetch:{tenant_id}:{inbound_reply_id}",
    )


async def ensure_inbound_reply_fetch(
    db: AsyncSession, *, tenant_id: uuid.UUID, inbound_reply_id: uuid.UUID
) -> OperationalJob:
    """Create the durable fetch job or safely reopen its terminal failed record."""
    key = f"inbound-reply-fetch:{tenant_id}:{inbound_reply_id}"
    existing = (
        await db.exec(
            select(OperationalJob)
            .where(OperationalJob.idempotency_key == key)
            .with_for_update()
        )
    ).first()
    if not existing:
        return enqueue_inbound_reply_fetch(
            db, tenant_id=tenant_id, inbound_reply_id=inbound_reply_id
        )
    if existing.status == "failed":
        existing.status = "pending"
        existing.attempts = 0
        existing.available_at = utcnow_naive()
        existing.locked_at = None
        existing.completed_at = None
        existing.last_error = None
        existing.updated_at = utcnow_naive()
        db.add(existing)
    return existing
