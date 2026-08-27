"""Durable, privacy-safe job contracts for company identification."""

from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.operational_job import OperationalJob
from app.services.operational_outbox import enqueue_operational_job

COMPANY_IDENTIFY_JOB_TYPE = "company_identify"


def enqueue_company_identification_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    network_observation_id: uuid.UUID,
) -> OperationalJob:
    """Queue a lookup by observation reference; never persist a raw IP in payload."""

    return enqueue_operational_job(
        db,
        job_type=COMPANY_IDENTIFY_JOB_TYPE,
        tenant_id=tenant_id,
        payload={"network_observation_id": str(network_observation_id)},
        idempotency_key=f"company-identify:{tenant_id}:{network_observation_id}",
    )
