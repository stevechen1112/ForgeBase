"""Shadow-mode company-identification runtime."""

from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Mapping
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlmodel import col, func, select

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session_ctx
from app.models.company_identification import (
    CompanyIdentification,
    CompanyIdentificationMode,
    GrowthAutomationPolicy,
    IdentificationStatus,
    NetworkEligibilityStatus,
    NetworkObservation,
    ProviderUsage,
)
from app.models.tracking_event import TrackingEvent
from app.models.visitor import Visitor
from app.services.company_identification.providers import (
    CompanyCandidate,
    CompanyLookupContext,
    CompanyLookupResult,
    CompanyProviderRetryableError,
    get_company_identification_provider,
)

logger = logging.getLogger(__name__)

_SENSITIVE_EVIDENCE_PARTS = {
    "email",
    "phone",
    "person",
    "contact",
    "individual",
    "address",
    "ip",
    "ipaddress",
    "raw",
    "payload",
}


def confidence_band(confidence: float, policy: GrowthAutomationPolicy) -> str:
    if confidence >= policy.high_confidence_threshold:
        return "high"
    if confidence >= policy.medium_confidence_threshold:
        return "medium"
    return "low"


def sanitize_provider_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Retain audit-safe scalar evidence and discard likely PII/raw payloads."""

    safe: dict[str, Any] = {}
    for key, value in evidence.items():
        normalized_key = str(key)[:80]
        lowered = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized_key).lower()
        key_parts = {part for part in re.split(r"[^a-z0-9]+", lowered) if part}
        sensitive_name = "name" in key_parts and bool(
            key_parts & {"person", "contact", "individual", "full", "first", "last"}
        )
        if key_parts & _SENSITIVE_EVIDENCE_PARTS or sensitive_name:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[normalized_key] = value[:500] if isinstance(value, str) else value
        elif isinstance(value, (list, tuple)):
            safe[normalized_key] = [
                item[:200] if isinstance(item, str) else item
                for item in value[:20]
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
    return safe


def _candidate_statuses(result: CompanyLookupResult) -> dict[str, str]:
    if len(result.candidates) < 2:
        return {
            candidate.candidate_key: IdentificationStatus.shadow.value
            for candidate in result.candidates
        }
    ranked = sorted(result.candidates, key=lambda candidate: candidate.confidence, reverse=True)
    top, second = ranked[0], ranked[1]
    conflict = (
        top.domain != second.domain
        and abs(top.confidence - second.confidence) <= 0.05
    )
    return {
        candidate.candidate_key: (
            IdentificationStatus.conflict.value
            if conflict and candidate in (top, second)
            else IdentificationStatus.shadow.value
        )
        for candidate in result.candidates
    }


async def _provider_circuit_is_open(db, *, tenant_id: uuid.UUID, provider: str) -> bool:
    failure_limit = max(1, settings.COMPANY_PROVIDER_CIRCUIT_FAILURES)
    since = utcnow_naive() - timedelta(
        seconds=max(1, settings.COMPANY_PROVIDER_CIRCUIT_COOLDOWN_SECONDS)
    )
    statuses = list(
        (
            await db.exec(
                select(ProviderUsage.response_status)
                .where(
                    ProviderUsage.tenant_id == tenant_id,
                    ProviderUsage.provider == provider,
                    ProviderUsage.operation == "company_identify",
                    ProviderUsage.cache_hit.is_(False),
                    ProviderUsage.created_at >= since,
                )
                .order_by(col(ProviderUsage.created_at).desc())
                .limit(failure_limit)
            )
        ).all()
    )
    return len(statuses) >= failure_limit and all(status == "error" for status in statuses)


async def _daily_provider_cost(db, *, tenant_id: uuid.UUID) -> Decimal:
    now = utcnow_naive()
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    value = (
        await db.exec(
            select(func.coalesce(func.sum(ProviderUsage.estimated_cost), 0)).where(
                ProviderUsage.tenant_id == tenant_id,
                ProviderUsage.created_at >= start_of_day,
            )
        )
    ).one()
    return Decimal(str(value))


async def _reuse_cached_candidates(
    db,
    *,
    observation: NetworkObservation,
    policy: GrowthAutomationPolicy,
    provider: str,
) -> int:
    now = utcnow_naive()
    cached = list(
        (
            await db.exec(
                select(CompanyIdentification)
                .join(
                    NetworkObservation,
                    CompanyIdentification.network_observation_id == NetworkObservation.id,
                )
                .where(
                    CompanyIdentification.tenant_id == observation.tenant_id,
                    CompanyIdentification.provider == provider,
                    CompanyIdentification.expires_at > now,
                    NetworkObservation.ip_hash == observation.ip_hash,
                    NetworkObservation.id != observation.id,
                )
                .order_by(col(CompanyIdentification.created_at).desc())
                .limit(20)
            )
        ).all()
    )
    if not cached:
        return 0
    source_observation_id = cached[0].network_observation_id
    source_rows = [
        row for row in cached if row.network_observation_id == source_observation_id
    ]
    for row in source_rows:
        candidate = CompanyCandidate(
            company_name=row.company_name,
            candidate_key=row.candidate_key,
            confidence=row.confidence,
            match_method=row.match_method,
            domain=row.domain,
            provider_company_id=row.provider_company_id,
            source_freshness=row.source_freshness,
            evidence=row.evidence_json,
        )
        await _upsert_candidate(
            db,
            observation=observation,
            policy=policy,
            provider=provider,
            candidate=candidate,
            status=(
                IdentificationStatus.conflict.value
                if row.status == IdentificationStatus.conflict.value
                else IdentificationStatus.shadow.value
            ),
        )
    return len(source_rows)


async def _upsert_candidate(
    db,
    *,
    observation: NetworkObservation,
    policy: GrowthAutomationPolicy,
    provider: str,
    candidate: CompanyCandidate,
    status: str,
) -> CompanyIdentification:
    candidate_key = candidate.candidate_key.strip()
    row = (
        await db.exec(
            select(CompanyIdentification).where(
                CompanyIdentification.tenant_id == observation.tenant_id,
                CompanyIdentification.network_observation_id == observation.id,
                CompanyIdentification.provider == provider,
                CompanyIdentification.candidate_key == candidate_key,
            )
        )
    ).first()
    now = utcnow_naive()
    if row is None:
        row = CompanyIdentification(
            tenant_id=observation.tenant_id,
            visitor_id=observation.visitor_id,
            network_observation_id=observation.id,
            company_name=candidate.company_name.strip(),
            domain=(candidate.domain or "").strip().lower() or None,
            provider_company_id=candidate.provider_company_id,
            provider=provider,
            candidate_key=candidate_key,
            confidence=candidate.confidence,
            confidence_band=confidence_band(candidate.confidence, policy),
            evidence_json=sanitize_provider_evidence(candidate.evidence),
            match_method=candidate.match_method,
            source_freshness=candidate.source_freshness,
            status=status,
            expires_at=observation.expires_at,
        )
    elif row.status in (IdentificationStatus.shadow.value, IdentificationStatus.conflict.value):
        row.company_name = candidate.company_name.strip()
        row.domain = (candidate.domain or "").strip().lower() or None
        row.provider_company_id = candidate.provider_company_id
        row.confidence = candidate.confidence
        row.confidence_band = confidence_band(candidate.confidence, policy)
        row.evidence_json = sanitize_provider_evidence(candidate.evidence)
        row.match_method = candidate.match_method
        row.source_freshness = candidate.source_freshness
        row.status = status
        row.updated_at = now
    db.add(row)
    return row


async def run_company_identification_job(
    network_observation_id: uuid.UUID,
    *,
    retry_count: int = 0,
) -> None:
    """Execute one policy-gated lookup and persist only safe, shadow results."""

    async with get_session_ctx() as db:
        observation = await db.get(NetworkObservation, network_observation_id)
        if not observation:
            raise ValueError("Network observation not found")
        policy = await db.get(GrowthAutomationPolicy, observation.tenant_id)
        if not policy or policy.company_identification_mode == CompanyIdentificationMode.off.value:
            return
        if observation.eligibility_status != NetworkEligibilityStatus.eligible.value:
            return
        visitor = await db.get(Visitor, observation.visitor_id)
        if (
            not visitor
            or visitor.tenant_id != observation.tenant_id
            or visitor.analytics_consent_status != "granted"
        ):
            observation.eligibility_status = NetworkEligibilityStatus.ineligible.value
            observation.ineligible_reason = "consent_withdrawn"
            db.add(observation)
            await db.commit()
            return
        if observation.expires_at <= utcnow_naive():
            observation.eligibility_status = NetworkEligibilityStatus.expired.value
            db.add(observation)
            await db.commit()
            return

        source_event = await db.get(TrackingEvent, observation.source_event_id)
        if (
            not source_event
            or source_event.tenant_id != observation.tenant_id
            or source_event.visitor_id != observation.visitor_id
            or not source_event.ip_address
        ):
            raise ValueError("Observation source event is unavailable or mismatched")

        adapter = get_company_identification_provider(policy.provider_name)
        context = CompanyLookupContext(
            tenant_id=observation.tenant_id,
            observation_id=observation.id,
            ip_address=source_event.ip_address,
            country=observation.country,
            asn=observation.asn,
        )
        started = time.monotonic()
        request_key = f"company-identify:{observation.id}:{adapter.name}"
        already_completed = (
            await db.exec(
                select(ProviderUsage.id).where(
                    ProviderUsage.tenant_id == observation.tenant_id,
                    ProviderUsage.provider == adapter.name,
                    ProviderUsage.operation == "company_identify",
                    ProviderUsage.request_key == request_key,
                    ProviderUsage.response_status.in_(["matched", "no_match", "cached_match"]),
                )
            )
        ).first()
        if already_completed:
            return
        cached_count = await _reuse_cached_candidates(
            db,
            observation=observation,
            policy=policy,
            provider=adapter.name,
        )
        if cached_count:
            db.add(
                ProviderUsage(
                    tenant_id=observation.tenant_id,
                    provider=adapter.name,
                    operation="company_identify",
                    request_key=request_key,
                    response_status="cached_match",
                    latency_ms=int((time.monotonic() - started) * 1000),
                    cache_hit=True,
                    retry_count=max(0, retry_count),
                )
            )
            await db.commit()
            return
        if await _provider_circuit_is_open(
            db,
            tenant_id=observation.tenant_id,
            provider=adapter.name,
        ):
            raise CompanyProviderRetryableError(
                "Company-identification provider circuit is open",
                retry_after_seconds=max(
                    1, settings.COMPANY_PROVIDER_CIRCUIT_COOLDOWN_SECONDS
                ),
            )
        estimated_next_cost = adapter.estimate_cost()
        if (
            estimated_next_cost > 0
            and await _daily_provider_cost(db, tenant_id=observation.tenant_id)
            + estimated_next_cost
            > policy.daily_provider_cost_limit
        ):
            observation.eligibility_status = NetworkEligibilityStatus.ineligible.value
            observation.ineligible_reason = "daily_cost_limit_exceeded"
            db.add(observation)
            db.add(
                ProviderUsage(
                    tenant_id=observation.tenant_id,
                    provider=adapter.name,
                    operation="company_identify",
                    request_key=request_key,
                    response_status="cost_guard",
                    latency_ms=int((time.monotonic() - started) * 1000),
                    retry_count=max(0, retry_count),
                )
            )
            await db.commit()
            return
        try:
            result = await adapter.identify_company(context)
            if result.provider != adapter.name:
                raise ValueError("Provider result name does not match adapter")
            risk = {
                "is_vpn": bool(result.metadata.get("is_vpn")),
                "is_proxy": bool(result.metadata.get("is_proxy")),
                "is_hosting": bool(result.metadata.get("is_hosting")),
            }
            observation.is_vpn = risk["is_vpn"]
            observation.is_proxy = risk["is_proxy"]
            observation.is_hosting = risk["is_hosting"]
            provider_rejected = bool(result.metadata.get("provider_network_rejected"))
            network_rejected = provider_rejected or any(risk.values())
            if network_rejected:
                observation.eligibility_status = NetworkEligibilityStatus.ineligible.value
                observation.ineligible_reason = "provider_network_risk"
            db.add(observation)
            candidates = () if network_rejected else result.candidates
            normalized_result = CompanyLookupResult(
                provider=result.provider,
                request_id=result.request_id,
                candidates=candidates,
                units=result.units,
                estimated_cost=result.estimated_cost,
            )
            statuses = _candidate_statuses(normalized_result)
            for candidate in candidates:
                await _upsert_candidate(
                    db,
                    observation=observation,
                    policy=policy,
                    provider=adapter.name,
                    candidate=candidate,
                    status=statuses[candidate.candidate_key],
                )
            db.add(
                ProviderUsage(
                    tenant_id=observation.tenant_id,
                    provider=adapter.name,
                    operation="company_identify",
                    request_key=request_key,
                    provider_request_id=result.request_id,
                    response_status=(
                        "network_rejected"
                        if network_rejected
                        else "matched" if candidates else "no_match"
                    ),
                    latency_ms=int((time.monotonic() - started) * 1000),
                    units=result.units,
                    estimated_cost=result.estimated_cost,
                    retry_count=max(0, retry_count),
                )
            )
            await db.commit()
        except Exception as exc:
            db.add(
                ProviderUsage(
                    tenant_id=observation.tenant_id,
                    provider=adapter.name,
                    operation="company_identify",
                    request_key=request_key,
                    response_status="error",
                    latency_ms=int((time.monotonic() - started) * 1000),
                    error_class=type(exc).__name__,
                    retry_count=max(0, retry_count),
                )
            )
            await db.commit()
            logger.warning(
                "Company identification failed for observation %s via %s",
                observation.id,
                adapter.name,
            )
            raise
