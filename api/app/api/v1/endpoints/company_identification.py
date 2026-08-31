"""Platform Shadow-Mode operations for inferred company candidates."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import require_superuser
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.company_identification import (
    CompanyIdentification,
    GrowthAutomationPolicy,
    IdentificationReview,
    IdentificationStatus,
    NetworkObservation,
    ProviderUsage,
)
from app.models.platform_audit_log import PlatformAuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.services.company_identification.providers import (
    available_provider_names,
    get_company_identification_provider,
)

router = APIRouter(prefix="/admin/company-identification", tags=["Company Identification"])


class GrowthPolicyUpdate(BaseModel):
    # Batch 2 deliberately exposes only OFF and SHADOW. Later modes require
    # their own reviewed implementation gates.
    company_identification_mode: Literal["off", "shadow"] = "off"
    provider_name: str = Field(default="mock", min_length=1, max_length=50)
    observation_retention_days: int = Field(default=30, ge=1, le=365)
    daily_lookup_quota: int = Field(default=100, ge=0, le=100_000)
    daily_provider_cost_limit: Decimal = Field(
        default=Decimal(10),
        ge=0,
        le=1_000_000,
    )
    medium_confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    high_confidence_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    allowed_countries: list[str] = Field(default_factory=list, max_length=250)

    @model_validator(mode="after")
    def validate_policy(self):
        if self.high_confidence_threshold < self.medium_confidence_threshold:
            raise ValueError("high confidence threshold must be >= medium threshold")
        normalized = []
        for country in self.allowed_countries:
            value = country.strip().upper()
            if len(value) != 2 or not value.isalpha():
                raise ValueError("allowed countries must use ISO alpha-2 codes")
            if value not in normalized:
                normalized.append(value)
        self.allowed_countries = normalized
        if self.company_identification_mode != "off" and self.provider_name not in available_provider_names():
            raise ValueError("provider is not configured in this deployment")
        return self


class IdentificationReviewIn(BaseModel):
    decision: Literal["confirm", "reject", "correct"]
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    corrected_company_name: str | None = Field(default=None, min_length=1, max_length=300)
    corrected_domain: str | None = Field(default=None, min_length=1, max_length=253)

    @model_validator(mode="after")
    def correction_requires_values(self):
        if self.decision == "correct" and not (
            self.corrected_company_name and self.corrected_domain
        ):
            raise ValueError("corrected company name and domain are required")
        if self.decision == "reject" and not (self.reason_code or "").strip():
            raise ValueError("rejection reason code is required")
        return self


def _normalized_domain(value: str) -> str:
    normalized = value.strip().lower().rstrip(".")
    parsed = urlsplit(f"//{normalized}")
    if (
        not parsed.hostname
        or parsed.hostname != normalized
        or "." not in normalized
        or any(not label or len(label) > 63 for label in normalized.split("."))
    ):
        raise HTTPException(status_code=422, detail="Corrected domain must be a hostname")
    return normalized


def _record_platform_audit(
    db: AsyncSession,
    actor: User,
    *,
    tenant_id: uuid.UUID,
    action: str,
    target_type: str,
    target_id: str,
    changes: dict,
) -> None:
    db.add(
        PlatformAuditLog(
            actor_user_id=actor.id,
            tenant_id=tenant_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            changes_json=json.dumps(changes, default=str, ensure_ascii=False),
        )
    )


def _policy_dict(policy: GrowthAutomationPolicy, *, persisted: bool = True) -> dict:
    return {
        "tenant_id": str(policy.tenant_id),
        "company_identification_mode": policy.company_identification_mode,
        "provider_name": policy.provider_name,
        "observation_retention_days": policy.observation_retention_days,
        "daily_lookup_quota": policy.daily_lookup_quota,
        "daily_provider_cost_limit": float(policy.daily_provider_cost_limit),
        "medium_confidence_threshold": policy.medium_confidence_threshold,
        "high_confidence_threshold": policy.high_confidence_threshold,
        "allowed_countries": policy.allowed_countries,
        "updated_by": str(policy.updated_by) if policy.updated_by else None,
        "created_at": policy.created_at.isoformat(),
        "updated_at": policy.updated_at.isoformat(),
        "persisted": persisted,
    }


def _candidate_dict(row: CompanyIdentification) -> dict:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "visitor_id": str(row.visitor_id),
        "network_observation_id": str(row.network_observation_id),
        "company_name": row.company_name,
        "domain": row.domain,
        "provider": row.provider,
        "provider_company_id": row.provider_company_id,
        "confidence": row.confidence,
        "confidence_band": row.confidence_band,
        "match_method": row.match_method,
        "evidence": row.evidence_json,
        "status": row.status,
        "source_freshness": row.source_freshness.isoformat() if row.source_freshness else None,
        "reviewed_by": str(row.reviewed_by) if row.reviewed_by else None,
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
        "review_note": row.review_note,
        "expires_at": row.expires_at.isoformat(),
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


async def _require_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/providers")
async def list_company_identification_providers(
    _: User = Depends(require_superuser),
):
    data = []
    for name in available_provider_names():
        adapter = get_company_identification_provider(name)
        data.append(
            {
                "name": name,
                "healthy": await adapter.healthcheck(),
                "estimated_cost": float(adapter.estimate_cost()),
            }
        )
    return {"data": data}


@router.get("/policies/{tenant_id}")
async def get_growth_policy(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
):
    await _require_tenant(db, tenant_id)
    policy = await db.get(GrowthAutomationPolicy, tenant_id)
    if policy:
        return _policy_dict(policy)
    return _policy_dict(GrowthAutomationPolicy(tenant_id=tenant_id), persisted=False)


@router.put("/policies/{tenant_id}")
async def update_growth_policy(
    tenant_id: uuid.UUID,
    body: GrowthPolicyUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
):
    await _require_tenant(db, tenant_id)
    policy = await db.get(GrowthAutomationPolicy, tenant_id)
    now = utcnow_naive()
    before = _policy_dict(policy) if policy else None
    if policy is None:
        policy = GrowthAutomationPolicy(tenant_id=tenant_id, created_at=now)
    for key, value in body.model_dump().items():
        setattr(policy, key, value)
    policy.updated_by = current_user.id
    policy.updated_at = now
    db.add(policy)
    _record_platform_audit(
        db,
        current_user,
        tenant_id=tenant_id,
        action="company_identification.policy_updated",
        target_type="growth_automation_policy",
        target_id=str(tenant_id),
        changes={"before": before, "after": body.model_dump()},
    )
    await db.commit()
    await db.refresh(policy)
    return _policy_dict(policy)


@router.get("/candidates")
async def list_company_candidates(
    tenant_id: uuid.UUID,
    candidate_status: Literal["shadow", "candidate", "confirmed", "rejected", "expired", "conflict"] | None = Query(default=None, alias="status"),
    confidence_band: Literal["low", "medium", "high"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
):
    await _require_tenant(db, tenant_id)
    query = (
        select(CompanyIdentification)
        .where(CompanyIdentification.tenant_id == tenant_id)
        .order_by(col(CompanyIdentification.created_at).desc())
    )
    if candidate_status:
        query = query.where(CompanyIdentification.status == candidate_status)
    if confidence_band:
        query = query.where(CompanyIdentification.confidence_band == confidence_band)
    rows = (await db.exec(query.offset(offset).limit(limit))).all()
    return {"data": [_candidate_dict(row) for row in rows], "limit": limit, "offset": offset}


@router.post("/candidates/{candidate_id}/review")
async def review_company_candidate(
    candidate_id: uuid.UUID,
    body: IdentificationReviewIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_superuser),
):
    row = await db.get(CompanyIdentification, candidate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Company candidate not found")
    now = utcnow_naive()
    if row.status == IdentificationStatus.expired.value or row.expires_at <= now:
        raise HTTPException(status_code=409, detail="Expired company candidates cannot be reviewed")
    if body.decision == "reject":
        row.status = IdentificationStatus.rejected.value
    else:
        row.status = IdentificationStatus.confirmed.value
    if body.decision == "correct":
        corrected_name = (body.corrected_company_name or "").strip()
        if not corrected_name:
            raise HTTPException(status_code=422, detail="Corrected company name must not be blank")
        corrected_domain = _normalized_domain(body.corrected_domain or "")
        row.company_name = corrected_name
        row.domain = corrected_domain
    row.reviewed_by = current_user.id
    row.reviewed_at = now
    row.review_note = body.note
    row.updated_at = now
    review = IdentificationReview(
        tenant_id=row.tenant_id,
        company_identification_id=row.id,
        decision=body.decision,
        corrected_company_name=body.corrected_company_name,
        corrected_domain=body.corrected_domain,
        reason_code=body.reason_code,
        note=body.note,
        reviewed_by=current_user.id,
        reviewed_at=now,
    )
    db.add(row)
    db.add(review)
    _record_platform_audit(
        db,
        current_user,
        tenant_id=row.tenant_id,
        action="company_identification.candidate_reviewed",
        target_type="company_identification",
        target_id=str(row.id),
        changes={
            "decision": body.decision,
            "reason_code": body.reason_code,
            "corrected_company_name": body.corrected_company_name,
            "corrected_domain": body.corrected_domain,
        },
    )
    await db.commit()
    await db.refresh(row)
    return _candidate_dict(row)


@router.get("/metrics")
async def company_identification_metrics(
    tenant_id: uuid.UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
    _: User = Depends(require_superuser),
):
    await _require_tenant(db, tenant_id)
    since = utcnow_naive() - timedelta(days=days)

    observation_rows = (
        await db.exec(
            select(NetworkObservation.eligibility_status, func.count(NetworkObservation.id))
            .where(
                NetworkObservation.tenant_id == tenant_id,
                NetworkObservation.created_at >= since,
            )
            .group_by(NetworkObservation.eligibility_status)
        )
    ).all()
    candidate_rows = (
        await db.exec(
            select(CompanyIdentification.status, func.count(CompanyIdentification.id))
            .where(
                CompanyIdentification.tenant_id == tenant_id,
                CompanyIdentification.reviewed_at >= since,
            )
            .group_by(CompanyIdentification.status)
        )
    ).all()
    usage_rows = (
        await db.exec(
            select(
                ProviderUsage.provider,
                ProviderUsage.response_status,
                func.count(ProviderUsage.id),
                func.coalesce(func.sum(ProviderUsage.units), 0),
                func.coalesce(func.sum(ProviderUsage.estimated_cost), 0),
                func.avg(ProviderUsage.latency_ms),
            )
            .where(ProviderUsage.tenant_id == tenant_id, ProviderUsage.created_at >= since)
            .group_by(ProviderUsage.provider, ProviderUsage.response_status)
        )
    ).all()

    high_confidence_count = (
        await db.exec(
            select(func.count(CompanyIdentification.id)).where(
                CompanyIdentification.tenant_id == tenant_id,
                CompanyIdentification.created_at >= since,
                CompanyIdentification.confidence_band == "high",
            )
        )
    ).one()

    high_reviewed = (
        await db.exec(
            select(CompanyIdentification.status, func.count(CompanyIdentification.id))
            .where(
                CompanyIdentification.tenant_id == tenant_id,
                CompanyIdentification.created_at >= since,
                CompanyIdentification.confidence_band == "high",
                CompanyIdentification.status.in_(["confirmed", "rejected"]),
            )
            .group_by(CompanyIdentification.status)
        )
    ).all()
    reviewed_counts = {status: count for status, count in high_reviewed}
    reviewed_total = reviewed_counts.get("confirmed", 0) + reviewed_counts.get("rejected", 0)
    precision = (
        reviewed_counts.get("confirmed", 0) / reviewed_total
        if reviewed_total
        else None
    )

    observation_counts = {status: count for status, count in observation_rows}
    candidate_counts = {status: count for status, count in candidate_rows}
    lookup_statuses = {
        "matched",
        "cached_match",
        "no_match",
        "network_rejected",
    }
    lookup_attempts = sum(
        requests
        for _, status, requests, _, _, _ in usage_rows
        if status in lookup_statuses
    )
    matched_lookups = sum(
        requests
        for _, status, requests, _, _, _ in usage_rows
        if status in {"matched", "cached_match"}
    )
    total_candidates = sum(candidate_counts.values())
    return {
        "tenant_id": str(tenant_id),
        "days": days,
        "observations": observation_counts,
        "candidates": candidate_counts,
        "lookup_attempts": lookup_attempts,
        "matched_lookups": matched_lookups,
        "match_rate": matched_lookups / lookup_attempts if lookup_attempts else None,
        "high_confidence_rate": (
            high_confidence_count / total_candidates if total_candidates else None
        ),
        "unknown_count": sum(
            requests
            for _, status, requests, _, _, _ in usage_rows
            if status == "no_match"
        ),
        "conflict_count": candidate_counts.get("conflict", 0),
        "total_estimated_cost": float(sum(row[4] for row in usage_rows)),
        "high_confidence_reviewed": reviewed_total,
        "high_confidence_precision": precision,
        "precision_gate": 0.90,
        "precision_gate_passed": precision is not None and precision >= 0.90,
        "provider_usage": [
            {
                "provider": provider,
                "status": status,
                "requests": requests,
                "units": int(units),
                "estimated_cost": float(cost),
                "average_latency_ms": float(average_latency or 0),
            }
            for provider, status, requests, units, cost, average_latency in usage_rows
        ],
    }
