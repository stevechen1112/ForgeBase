"""Consent withdrawal and TTL deletion for company-identification evidence."""

from __future__ import annotations

import uuid
from collections.abc import Collection

from sqlalchemy import delete, or_
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.datetime import utcnow_naive
from app.models.company_identification import (
    CompanyIdentification,
    NetworkObservation,
    ProviderUsage,
)
from app.models.contact_enrichment import ContactCandidate
from app.models.operational_job import OperationalJob
from app.models.outreach import OutreachMessage


async def _delete_jobs_referencing_observations(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    observation_ids: Collection[uuid.UUID],
) -> dict[str, int]:
    if not observation_ids:
        return {"company_jobs": 0, "provider_usage": 0}
    idempotency_keys = [
        f"company-identify:{tenant_id}:{observation_id}"
        for observation_id in observation_ids
    ]
    request_keys = [
        f"company-identify:{observation_id}:" for observation_id in observation_ids
    ]
    jobs = await db.exec(
        delete(OperationalJob).where(
            OperationalJob.tenant_id == tenant_id,
            OperationalJob.job_type == "company_identify",
            col(OperationalJob.idempotency_key).in_(idempotency_keys),
        )
    )
    usage_filters = [
        ProviderUsage.request_key.startswith(prefix) for prefix in request_keys
    ]
    usage = await db.exec(
        delete(ProviderUsage).where(
            ProviderUsage.tenant_id == tenant_id,
            ProviderUsage.operation == "company_identify",
            or_(*usage_filters),
        )
    )
    provider_usage_count = int(usage.rowcount or 0)
    return {
        "company_jobs": int(jobs.rowcount or 0),
        "provider_usage": provider_usage_count,
    }


async def delete_visitor_company_evidence(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    visitor_id: uuid.UUID,
) -> dict[str, int]:
    observation_ids = list(
        (
            await db.exec(
                select(NetworkObservation.id).where(
                    NetworkObservation.tenant_id == tenant_id,
                    NetworkObservation.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    company_rows = list(
        (
            await db.exec(
                select(
                    CompanyIdentification.id,
                    CompanyIdentification.network_observation_id,
                ).where(
                    CompanyIdentification.tenant_id == tenant_id,
                    CompanyIdentification.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    company_ids = [row[0] for row in company_rows]
    protected_company_ids: set[uuid.UUID] = set()
    if company_ids:
        protected_company_ids.update(
            row
            for row in (
                await db.exec(
                    select(ContactCandidate.company_identification_id).where(
                        col(ContactCandidate.company_identification_id).in_(company_ids),
                        ContactCandidate.status == "converted",
                    )
                )
            ).all()
            if row is not None
        )
        protected_company_ids.update(
            (
                await db.exec(
                    select(OutreachMessage.company_identification_id).where(
                        col(OutreachMessage.company_identification_id).in_(company_ids)
                    )
                )
            ).all()
        )
    deletable_company_ids = [
        company_id for company_id in company_ids if company_id not in protected_company_ids
    ]
    protected_observation_ids = {
        observation_id
        for company_id, observation_id in company_rows
        if company_id in protected_company_ids
    }
    deletable_observation_ids = [
        observation_id
        for observation_id in observation_ids
        if observation_id not in protected_observation_ids
    ]
    candidate_hashes = list(
        (
            await db.exec(
                select(ContactCandidate.email_hash).where(
                    ContactCandidate.tenant_id == tenant_id,
                    col(ContactCandidate.company_identification_id).in_(company_ids),
                    ContactCandidate.status != "converted",
                    ~select(OutreachMessage.id)
                    .where(
                        OutreachMessage.contact_candidate_id == ContactCandidate.id
                    )
                    .exists(),
                )
            )
        ).all()
    ) if company_ids else []
    candidate_ids = list(
        (
            await db.exec(
                select(ContactCandidate.id).where(
                    ContactCandidate.tenant_id == tenant_id,
                    col(ContactCandidate.company_identification_id).in_(company_ids),
                )
            )
        ).all()
    ) if company_ids else []
    outreach_job_filters = [
        OperationalJob.idempotency_key.startswith(
            f"journey-summarize:{tenant_id}:{candidate_id}:"
        )
        for candidate_id in candidate_ids
    ] + [
        OperationalJob.payload_json.contains(str(candidate_id))
        for candidate_id in candidate_ids
    ]
    outreach_jobs = await db.exec(
        delete(OperationalJob).where(
            OperationalJob.tenant_id == tenant_id,
            OperationalJob.job_type.in_(["journey_summarize", "outreach_draft"]),
            or_(*outreach_job_filters),
        )
    ) if outreach_job_filters else None
    contact_jobs = await db.exec(
        delete(OperationalJob).where(
            OperationalJob.tenant_id == tenant_id,
            OperationalJob.job_type == "contact_enrich",
            or_(
                *[
                    OperationalJob.idempotency_key.startswith(
                        f"contact-enrich:{tenant_id}:{company_id}:"
                    )
                    for company_id in deletable_company_ids
                ]
            ),
        )
    ) if deletable_company_ids else None
    contact_usage_filters = [
        ProviderUsage.request_key == str(company_id) for company_id in deletable_company_ids
    ] + [
        ProviderUsage.request_key == f"candidate:{digest[:12]}"
        for digest in candidate_hashes
    ]
    contact_usage = await db.exec(
        delete(ProviderUsage).where(
            ProviderUsage.tenant_id == tenant_id,
            ProviderUsage.operation.in_(["contact_search", "email_verify"]),
            or_(*contact_usage_filters),
        )
    ) if contact_usage_filters else None
    unconverted_candidates = await db.exec(
        delete(ContactCandidate).where(
            ContactCandidate.tenant_id == tenant_id,
            col(ContactCandidate.company_identification_id).in_(company_ids),
            ContactCandidate.status != "converted",
            ~select(OutreachMessage.id)
            .where(OutreachMessage.contact_candidate_id == ContactCandidate.id)
            .exists(),
        )
    ) if company_ids else None
    deleted_references = await _delete_jobs_referencing_observations(
        db,
        tenant_id=tenant_id,
        observation_ids=deletable_observation_ids,
    )
    result = await db.exec(
        delete(NetworkObservation).where(
            NetworkObservation.tenant_id == tenant_id,
            col(NetworkObservation.id).in_(deletable_observation_ids),
        )
    )
    deleted = {
        "network_observations": int(result.rowcount or 0),
        "contact_candidates": int(unconverted_candidates.rowcount or 0)
        if unconverted_candidates is not None
        else 0,
        "contact_jobs": int(contact_jobs.rowcount or 0) if contact_jobs is not None else 0,
        "contact_provider_usage": int(contact_usage.rowcount or 0)
        if contact_usage is not None
        else 0,
        **deleted_references,
    }
    if protected_observation_ids:
        deleted["preserved_business_company_evidence"] = len(
            protected_observation_ids
        )
    outreach_job_count = int(outreach_jobs.rowcount or 0) if outreach_jobs is not None else 0
    if outreach_job_count:
        deleted["outreach_jobs"] = outreach_job_count
    return deleted


async def purge_expired_company_evidence(db: AsyncSession) -> dict[str, int]:
    rows = list(
        (
            await db.exec(
                select(NetworkObservation.id, NetworkObservation.tenant_id).where(
                    NetworkObservation.expires_at <= utcnow_naive()
                )
            )
        ).all()
    )
    protected_rows = set(
        (
            await db.exec(
                select(CompanyIdentification.network_observation_id)
                .join(
                    ContactCandidate,
                    ContactCandidate.company_identification_id == CompanyIdentification.id,
                )
                .where(ContactCandidate.status == "converted")
                .where(
                    col(CompanyIdentification.network_observation_id).in_(
                        [row[0] for row in rows]
                    )
                )
            )
        ).all()
    )
    protected_rows.update(
        (
            await db.exec(
                select(CompanyIdentification.network_observation_id)
                .join(
                    OutreachMessage,
                    OutreachMessage.company_identification_id == CompanyIdentification.id,
                )
                .where(
                    col(CompanyIdentification.network_observation_id).in_(
                        [row[0] for row in rows]
                    )
                )
            )
        ).all()
    )
    rows = [row for row in rows if row[0] not in protected_rows]
    deleted_references = {"company_jobs": 0, "provider_usage": 0}
    tenant_observations: dict[uuid.UUID, list[uuid.UUID]] = {}
    for observation_id, tenant_id in rows:
        tenant_observations.setdefault(tenant_id, []).append(observation_id)
    for tenant_id, observation_ids in tenant_observations.items():
        tenant_deleted = await _delete_jobs_referencing_observations(
            db,
            tenant_id=tenant_id,
            observation_ids=observation_ids,
        )
        for key, value in tenant_deleted.items():
            deleted_references[key] += value
    result = await db.exec(
        delete(NetworkObservation).where(
            col(NetworkObservation.id).in_([row[0] for row in rows])
        )
    )
    return {
        "network_observations": int(result.rowcount or 0),
        "preserved_business_company_evidence": len(protected_rows),
        **deleted_references,
    }
