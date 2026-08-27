"""Platform review operations for company-related contact candidates."""

from __future__ import annotations

import json
import time
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_superuser
from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt
from app.db.session import get_session
from app.models.company_identification import CompanyIdentification, ProviderUsage
from app.models.contact import Contact
from app.models.contact_enrichment import (
    ContactCandidate,
    ContactCandidateReview,
    ContactPersonaPolicy,
)
from app.models.email_delivery import EmailSuppression
from app.models.platform_audit_log import PlatformAuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.services.contact_enrichment.jobs import enqueue_contact_enrichment_job
from app.services.contact_enrichment.providers import (
    ContactProviderError,
    available_contact_provider_names,
    available_verification_provider_names,
    get_contact_provider,
    get_verification_provider,
)
from app.services.contact_enrichment.runtime import today_contact_usage
from app.services.email_governance import email_hash, normalize_email

router = APIRouter(prefix="/admin/contact-enrichment", tags=["Contact Enrichment"])


class PersonaPolicyUpdate(BaseModel):
    mode: Literal["off", "review_only"] = "off"
    contact_provider_name: str = Field(default="mock", min_length=1, max_length=50)
    verification_provider_name: str = Field(default="mock", min_length=1, max_length=50)
    target_departments: list[str] = Field(default_factory=list, max_length=25)
    target_titles: list[str] = Field(default_factory=list, max_length=50)
    target_seniorities: list[str] = Field(default_factory=list, max_length=20)
    target_locations: list[str] = Field(default_factory=list, max_length=50)
    excluded_title_terms: list[str] = Field(default_factory=list, max_length=50)
    min_relevance_score: int = Field(default=60, ge=0, le=100)
    candidate_retention_days: int = Field(default=90, ge=1, le=365)
    max_candidates_per_company: int = Field(default=5, ge=1, le=25)
    daily_lookup_quota: int = Field(default=25, ge=0, le=10_000)
    daily_provider_cost_limit: Decimal = Field(default=Decimal(5), ge=0, le=1_000_000)

    @model_validator(mode="after")
    def validate_policy(self):
        for field_name in (
            "target_departments", "target_titles", "target_seniorities",
            "target_locations", "excluded_title_terms",
        ):
            values: list[str] = getattr(self, field_name)
            normalized: list[str] = []
            for raw in values:
                value = raw.strip()
                if not value or len(value) > 100:
                    raise ValueError(f"{field_name} values must be 1-100 characters")
                if value.lower() not in {item.lower() for item in normalized}:
                    normalized.append(value)
            setattr(self, field_name, normalized)
        if self.mode == "review_only":
            if not (self.target_departments or self.target_titles):
                raise ValueError("review_only requires target departments or titles")
            if self.contact_provider_name not in available_contact_provider_names():
                raise ValueError("contact provider is not configured in this deployment")
            if self.verification_provider_name not in available_verification_provider_names():
                raise ValueError("verification provider is not configured in this deployment")
        return self


class CandidateDecisionIn(BaseModel):
    decision: Literal["approve", "reject", "do_not_contact"]
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def reason_required(self):
        if self.decision in {"reject", "do_not_contact"} and not (self.reason_code or "").strip():
            raise ValueError("rejection and do-not-contact decisions require a reason code")
        return self


class ConvertCandidateIn(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


def _audit(
    db: AsyncSession,
    actor: User,
    tenant_id: uuid.UUID,
    action: str,
    target_id: uuid.UUID,
    changes: dict,
    *,
    target_type: str = "contact_candidate",
) -> None:
    db.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            changes_json=json.dumps(changes, ensure_ascii=False, default=str),
        )
    )


def _policy_dict(row: ContactPersonaPolicy, *, persisted: bool = True) -> dict:
    return {
        "tenant_id": str(row.tenant_id), "mode": row.mode,
        "contact_provider_name": row.contact_provider_name,
        "verification_provider_name": row.verification_provider_name,
        "target_departments": row.target_departments, "target_titles": row.target_titles,
        "target_seniorities": row.target_seniorities, "target_locations": row.target_locations,
        "excluded_title_terms": row.excluded_title_terms,
        "min_relevance_score": row.min_relevance_score,
        "candidate_retention_days": row.candidate_retention_days,
        "max_candidates_per_company": row.max_candidates_per_company,
        "daily_lookup_quota": row.daily_lookup_quota,
        "daily_provider_cost_limit": float(row.daily_provider_cost_limit),
        "updated_by": str(row.updated_by) if row.updated_by else None,
        "updated_at": row.updated_at.isoformat(), "persisted": persisted,
    }


def _candidate_dict(row: ContactCandidate, company: CompanyIdentification | None = None) -> dict:
    return {
        "id": str(row.id), "tenant_id": str(row.tenant_id),
        "company_identification_id": str(row.company_identification_id)
        if row.company_identification_id
        else None,
        "company_name": company.company_name if company else row.source_company_name,
        "company_domain": company.domain if company else row.source_company_domain,
        "identity_notice": "公司相關聯絡窗口候選；不代表此人就是匿名訪客",
        "full_name": row.full_name, "job_title": row.job_title,
        "department": row.department, "seniority": row.seniority, "location": row.location,
        "email_masked": row.email_masked, "verification_status": row.verification_status,
        "verification_provider": row.verification_provider,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "source_provider": row.source_provider, "source_url": row.source_url,
        "source_freshness": row.source_freshness.isoformat() if row.source_freshness else None,
        "relevance_score": row.relevance_score, "relevance_reasons": row.relevance_reasons,
        "confidence": row.confidence, "status": row.status,
        "review_reason_code": row.review_reason_code, "review_note": row.review_note,
        "reviewed_by": str(row.reviewed_by) if row.reviewed_by else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "converted_contact_id": str(row.converted_contact_id) if row.converted_contact_id else None,
        "expires_at": row.expires_at.isoformat(), "created_at": row.created_at.isoformat(),
    }


async def _tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    row = await db.get(Tenant, tenant_id)
    if not row:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return row


@router.get("/providers")
async def providers(_: User = Depends(require_superuser)):
    contact = []
    for name in available_contact_provider_names():
        adapter = get_contact_provider(name)
        contact.append({"name": name, "healthy": await adapter.healthcheck(), "estimated_cost": float(adapter.estimate_cost())})
    verification = []
    for name in available_verification_provider_names():
        adapter = get_verification_provider(name)
        verification.append({"name": name, "healthy": await adapter.healthcheck(), "estimated_cost": float(adapter.estimate_cost())})
    return {"contact": contact, "verification": verification}


@router.get("/policies/{tenant_id}")
async def get_policy(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_session), _: User = Depends(require_superuser)):
    await _tenant(db, tenant_id)
    row = await db.get(ContactPersonaPolicy, tenant_id)
    return _policy_dict(row) if row else _policy_dict(ContactPersonaPolicy(tenant_id=tenant_id), persisted=False)


@router.put("/policies/{tenant_id}")
async def update_policy(tenant_id: uuid.UUID, body: PersonaPolicyUpdate, db: AsyncSession = Depends(get_session), actor: User = Depends(require_superuser)):
    await _tenant(db, tenant_id)
    row = await db.get(ContactPersonaPolicy, tenant_id)
    now = utcnow_naive()
    before = _policy_dict(row) if row else None
    if row is None:
        row = ContactPersonaPolicy(tenant_id=tenant_id, created_at=now)
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by = actor.id
    row.updated_at = now
    db.add(row)
    _audit(db, actor, tenant_id, "contact_enrichment.policy_updated", tenant_id, {"before": before, "after": body.model_dump()}, target_type="contact_persona_policy")
    await db.commit()
    await db.refresh(row)
    return _policy_dict(row)


@router.post("/companies/{company_id}/enqueue")
async def enqueue(company_id: uuid.UUID, db: AsyncSession = Depends(get_session), actor: User = Depends(require_superuser)):
    company = await db.get(CompanyIdentification, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company candidate not found")
    policy = await db.get(ContactPersonaPolicy, company.tenant_id)
    if not policy or policy.mode != "review_only":
        raise HTTPException(status_code=409, detail="Contact enrichment is off")
    now = utcnow_naive()
    if company.status != "confirmed" or company.expires_at <= now or not company.domain:
        raise HTTPException(status_code=409, detail="A current confirmed company with a domain is required")
    job = enqueue_contact_enrichment_job(db, tenant_id=company.tenant_id, company_identification_id=company.id)
    _audit(db, actor, company.tenant_id, "contact_enrichment.enqueued", company.id, {"job_id": str(job.id)}, target_type="company_identification")
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="An enrichment run is already queued for this company today") from exc
    return {"job_id": str(job.id), "status": job.status}


@router.get("/candidates")
async def list_candidates(
    tenant_id: uuid.UUID, company_identification_id: uuid.UUID | None = None,
    candidate_status: Literal["candidate", "approved", "rejected", "converted", "expired", "do_not_contact"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session), _: User = Depends(require_superuser),
):
    await _tenant(db, tenant_id)
    query = select(ContactCandidate).where(ContactCandidate.tenant_id == tenant_id).order_by(col(ContactCandidate.created_at).desc())
    if company_identification_id:
        query = query.where(ContactCandidate.company_identification_id == company_identification_id)
    if candidate_status:
        query = query.where(ContactCandidate.status == candidate_status)
    rows = (await db.exec(query.offset(offset).limit(limit))).all()
    company_ids = {row.company_identification_id for row in rows if row.company_identification_id}
    companies = (await db.exec(select(CompanyIdentification).where(col(CompanyIdentification.id).in_(company_ids)))).all() if company_ids else []
    company_map = {row.id: row for row in companies}
    return {"data": [_candidate_dict(row, company_map.get(row.company_identification_id)) for row in rows], "limit": limit, "offset": offset}


@router.post("/candidates/{candidate_id}/review")
async def review_candidate(candidate_id: uuid.UUID, body: CandidateDecisionIn, db: AsyncSession = Depends(get_session), actor: User = Depends(require_superuser)):
    row = (await db.exec(select(ContactCandidate).where(ContactCandidate.id == candidate_id).with_for_update())).first()
    if not row:
        raise HTTPException(status_code=404, detail="Contact candidate not found")
    now = utcnow_naive()
    if row.expires_at <= now or row.status not in {"candidate", "approved"}:
        raise HTTPException(status_code=409, detail="Candidate is no longer reviewable")
    if body.decision == "approve":
        if row.status != "candidate":
            raise HTTPException(status_code=409, detail="Only pending candidates can be approved")
        if row.verification_status == "invalid":
            raise HTTPException(status_code=409, detail="Invalid email candidates cannot be approved")
        row.status = "approved"
    elif body.decision == "reject":
        row.status = "rejected"
    else:
        row.status = "do_not_contact"
        # Retain only the keyed hash and mask needed to enforce DNC. The
        # candidate can never be converted or reverified after this decision.
        row.email_ciphertext = ""
        row.full_name = "Suppressed business contact"
        row.job_title = None
        row.department = None
        row.seniority = None
        row.location = None
        row.source_url = None
    row.reviewed_by = actor.id
    row.reviewed_at = now
    row.review_reason_code = body.reason_code
    row.review_note = body.note
    row.updated_at = now
    db.add(row)
    db.add(ContactCandidateReview(tenant_id=row.tenant_id, contact_candidate_id=row.id, decision=body.decision, reason_code=body.reason_code, note=body.note, reviewer_id=actor.id, created_at=now))
    _audit(db, actor, row.tenant_id, "contact_enrichment.candidate_reviewed", row.id, body.model_dump())
    await db.commit()
    await db.refresh(row)
    company = await db.get(CompanyIdentification, row.company_identification_id)
    return _candidate_dict(row, company)


@router.post("/candidates/{candidate_id}/verify-email")
async def verify_candidate(candidate_id: uuid.UUID, db: AsyncSession = Depends(get_session), actor: User = Depends(require_superuser)):
    row = await db.get(ContactCandidate, candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Contact candidate not found")
    if row.status in {"converted", "expired", "do_not_contact"} or row.expires_at <= utcnow_naive():
        raise HTTPException(status_code=409, detail="Candidate cannot be reverified")
    policy = await db.get(ContactPersonaPolicy, row.tenant_id)
    if not policy or policy.mode != "review_only":
        raise HTTPException(status_code=409, detail="Contact enrichment is off")
    verifier = get_verification_provider(policy.verification_provider_name)
    lookup_count, cost = await today_contact_usage(db, row.tenant_id)
    if lookup_count >= policy.daily_lookup_quota:
        raise HTTPException(status_code=429, detail="Tenant contact lookup quota is exhausted")
    if cost + verifier.estimate_cost() > policy.daily_provider_cost_limit:
        raise HTTPException(status_code=409, detail="Tenant contact provider cost limit would be exceeded")
    try:
        address = normalize_email(decrypt(row.email_ciphertext))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Candidate email cannot be decrypted") from exc
    if email_hash(address) != row.email_hash or address.partition("@")[2] != row.source_company_domain:
        raise HTTPException(status_code=409, detail="Candidate email integrity or company-domain check failed")
    started = time.perf_counter()
    try:
        result = await verifier.verify(address)
    except ContactProviderError as exc:
        latency_ms = max(0, round((time.perf_counter() - started) * 1000))
        db.add(
            ProviderUsage(
                tenant_id=row.tenant_id,
                provider=verifier.name,
                operation="email_verify",
                request_key=f"candidate:{row.email_hash[:12]}",
                response_status="error",
                latency_ms=latency_ms,
                error_class=type(exc).__name__,
            )
        )
        await db.commit()
        raise HTTPException(
            status_code=502, detail="Email verification provider failed"
        ) from exc
    latency_ms = max(0, round((time.perf_counter() - started) * 1000))
    db.add(
        ProviderUsage(
            tenant_id=row.tenant_id,
            provider=result.provider,
            operation="email_verify",
            request_key=f"candidate:{row.email_hash[:12]}",
            provider_request_id=result.request_id,
            response_status=result.status,
            latency_ms=latency_ms,
            units=result.units,
            estimated_cost=result.estimated_cost,
        )
    )
    row.verification_status = result.status
    row.verification_provider = result.provider
    row.verified_at = result.checked_at or utcnow_naive()
    row.updated_at = utcnow_naive()
    db.add(row)
    _audit(db, actor, row.tenant_id, "contact_enrichment.email_reverified", row.id, {"status": result.status, "provider": result.provider})
    await db.commit()
    await db.refresh(row)
    company = await db.get(CompanyIdentification, row.company_identification_id) if row.company_identification_id else None
    return _candidate_dict(row, company)


@router.post("/candidates/{candidate_id}/convert-to-contact")
async def convert_candidate(candidate_id: uuid.UUID, body: ConvertCandidateIn, db: AsyncSession = Depends(get_session), actor: User = Depends(require_superuser)):
    row = (await db.exec(select(ContactCandidate).where(ContactCandidate.id == candidate_id).with_for_update())).first()
    if not row:
        raise HTTPException(status_code=404, detail="Contact candidate not found")
    now = utcnow_naive()
    if row.status != "approved" or row.expires_at <= now:
        raise HTTPException(status_code=409, detail="Only a current approved candidate can be converted")
    if row.verification_status != "verified":
        raise HTTPException(status_code=409, detail="Only verified business emails can be converted")
    policy = await db.get(ContactPersonaPolicy, row.tenant_id)
    if not policy or row.relevance_score < policy.min_relevance_score:
        raise HTTPException(status_code=409, detail="Candidate does not meet the tenant relevance gate")
    # Lock every same-address candidate before checking/creating Contact so two
    # companies cannot race through the tenant-scoped Contact unique key.
    await db.exec(
        select(ContactCandidate.id).where(
            ContactCandidate.tenant_id == row.tenant_id,
            ContactCandidate.email_hash == row.email_hash,
        ).with_for_update()
    )
    suppressed = (await db.exec(select(EmailSuppression.id).where(EmailSuppression.scope_key == "global", EmailSuppression.email_hash == row.email_hash, EmailSuppression.active.is_(True)))).first()
    if suppressed:
        raise HTTPException(status_code=409, detail="Candidate is suppressed")
    company = await db.get(CompanyIdentification, row.company_identification_id) if row.company_identification_id else None
    if not company or company.status != "confirmed" or company.expires_at <= now or not company.domain:
        raise HTTPException(status_code=409, detail="Confirmed company evidence is no longer current")
    address = normalize_email(decrypt(row.email_ciphertext))
    if email_hash(address) != row.email_hash or address.partition("@")[2] != company.domain.lower():
        raise HTTPException(status_code=409, detail="Candidate email integrity or company-domain check failed")
    contact = (await db.exec(select(Contact).where(Contact.tenant_id == row.tenant_id, Contact.email == address).with_for_update())).first()
    if contact is None:
        contact = Contact(
            tenant_id=row.tenant_id, email=address, full_name=row.full_name,
            company_name=company.company_name[:100], country=row.location[:50] if row.location else None,
            job_title=row.job_title[:80] if row.job_title else None,
            source_type="contact_candidate", source_reference_id=row.id,
            notes="由人工核准的公司相關聯絡窗口候選轉入；不代表此人就是原匿名訪客。",
            created_at=now, updated_at=now,
        )
        db.add(contact)
        await db.flush()
    row.status = "converted"
    row.converted_contact_id = contact.id
    row.reviewed_by = actor.id
    row.reviewed_at = now
    row.review_note = body.note
    row.updated_at = now
    db.add(row)
    db.add(ContactCandidateReview(tenant_id=row.tenant_id, contact_candidate_id=row.id, decision="convert", note=body.note, reviewer_id=actor.id, resulting_contact_id=contact.id, created_at=now))
    _audit(db, actor, row.tenant_id, "contact_enrichment.converted", row.id, {"contact_id": str(contact.id), "visitor_linked": False})
    await db.commit()
    return {"candidate": _candidate_dict(row, company), "contact_id": str(contact.id)}


@router.get("/metrics")
async def contact_enrichment_metrics(
    tenant_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
):
    await _tenant(db, tenant_id)
    since = utcnow_naive() - timedelta(days=days)
    statuses = (
        await db.exec(
            select(ContactCandidate.status, func.count(ContactCandidate.id))
            .where(
                ContactCandidate.tenant_id == tenant_id,
                ContactCandidate.created_at >= since,
            )
            .group_by(ContactCandidate.status)
        )
    ).all()
    verifications = (
        await db.exec(
            select(
                ContactCandidate.verification_status,
                func.count(ContactCandidate.id),
            )
            .where(
                ContactCandidate.tenant_id == tenant_id,
                ContactCandidate.created_at >= since,
            )
            .group_by(ContactCandidate.verification_status)
        )
    ).all()
    average_relevance = (
        await db.exec(
            select(func.avg(ContactCandidate.relevance_score)).where(
                ContactCandidate.tenant_id == tenant_id,
                ContactCandidate.created_at >= since,
            )
        )
    ).one()
    usage_rows = (
        await db.exec(
            select(
                ProviderUsage.provider,
                ProviderUsage.operation,
                func.count(ProviderUsage.id),
                func.coalesce(func.sum(ProviderUsage.units), 0),
                func.coalesce(func.sum(ProviderUsage.estimated_cost), 0),
                func.avg(ProviderUsage.latency_ms),
            )
            .where(
                ProviderUsage.tenant_id == tenant_id,
                ProviderUsage.operation.in_(["contact_search", "email_verify"]),
                ProviderUsage.created_at >= since,
            )
            .group_by(ProviderUsage.provider, ProviderUsage.operation)
        )
    ).all()
    status_counts = {status: count for status, count in statuses}
    verification_counts = {status: count for status, count in verifications}
    reviewed = sum(
        status_counts.get(value, 0)
        for value in ("approved", "rejected", "converted", "do_not_contact")
    )
    accepted = status_counts.get("approved", 0) + status_counts.get("converted", 0)
    total = sum(status_counts.values())
    return {
        "tenant_id": str(tenant_id),
        "days": days,
        "statuses": status_counts,
        "verifications": verification_counts,
        "candidate_count": total,
        "reviewed_count": reviewed,
        "approval_rate": accepted / reviewed if reviewed else None,
        "verified_rate": verification_counts.get("verified", 0) / total if total else None,
        "average_relevance": float(average_relevance or 0),
        "provider_usage": [
            {
                "provider": provider,
                "operation": operation,
                "requests": requests,
                "units": int(units),
                "estimated_cost": float(cost),
                "average_latency_ms": float(latency or 0),
            }
            for provider, operation, requests, units, cost, latency in usage_rows
        ],
    }
