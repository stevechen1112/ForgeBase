from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.operational_job import OperationalJob
from app.services.operational_outbox import enqueue_operational_job

JOURNEY_SUMMARIZE_JOB_TYPE = "journey_summarize"
OUTREACH_DRAFT_JOB_TYPE = "outreach_draft"
OUTREACH_SEND_JOB_TYPE = "outreach_send"


def enqueue_journey_summarize_job(
    db: AsyncSession, *, tenant_id: uuid.UUID, candidate_id: uuid.UUID
) -> OperationalJob:
    day = utcnow_naive().date().isoformat()
    return enqueue_operational_job(
        db,
        job_type=JOURNEY_SUMMARIZE_JOB_TYPE,
        tenant_id=tenant_id,
        payload={"contact_candidate_id": str(candidate_id)},
        idempotency_key=f"journey-summarize:{tenant_id}:{candidate_id}:{day}",
    )


def enqueue_outreach_draft_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> OperationalJob:
    return enqueue_operational_job(
        db,
        job_type=OUTREACH_DRAFT_JOB_TYPE,
        tenant_id=tenant_id,
        payload={
            "journey_snapshot_id": str(snapshot_id),
            "contact_candidate_id": str(candidate_id),
        },
        idempotency_key=f"outreach-draft:{tenant_id}:{snapshot_id}:{candidate_id}",
    )


def enqueue_outreach_send_job(
    db: AsyncSession, *, tenant_id: uuid.UUID, message_id: uuid.UUID, available_at=None
) -> OperationalJob:
    job = enqueue_operational_job(
        db,
        job_type=OUTREACH_SEND_JOB_TYPE,
        tenant_id=tenant_id,
        payload={"outreach_message_id": str(message_id)},
        idempotency_key=f"outreach-send:{tenant_id}:{message_id}",
    )
    if available_at is not None:
        job.available_at = available_at
    return job
