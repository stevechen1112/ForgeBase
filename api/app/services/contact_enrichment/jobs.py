from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.operational_job import OperationalJob
from app.services.operational_outbox import enqueue_operational_job

CONTACT_ENRICH_JOB_TYPE = "contact_enrich"


def enqueue_contact_enrichment_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    company_identification_id: uuid.UUID,
) -> OperationalJob:
    return enqueue_operational_job(
        db,
        job_type=CONTACT_ENRICH_JOB_TYPE,
        tenant_id=tenant_id,
        payload={"company_identification_id": str(company_identification_id)},
        idempotency_key=(
            f"contact-enrich:{tenant_id}:{company_identification_id}:"
            f"{utcnow_naive().date().isoformat()}"
        ),
    )
