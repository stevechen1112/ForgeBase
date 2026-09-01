"""Controlled contact-candidate discovery runtime.

This service persists only normalized fields, encrypted email addresses and
masked/hash derivatives. Provider responses and plaintext emails are never
logged or placed in OperationalJob payloads.
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import delete, func
from sqlmodel import col, select

from app.core.datetime import utcnow_naive
from app.core.encryption import encrypt
from app.db.session import get_session_ctx
from app.models.company_identification import CompanyIdentification, ProviderUsage
from app.models.contact_enrichment import (
    ContactCandidate,
    ContactCandidateStatus,
    ContactPersonaPolicy,
)
from app.models.email_delivery import EmailSuppression
from app.models.outreach import OutreachMessage
from app.models.visitor import Visitor
from app.services.contact_enrichment.providers import (
    ContactProviderCandidate,
    ContactProviderPermanentError,
    ContactSearchContext,
    ContactSearchResult,
    EmailVerificationResult,
    get_contact_provider,
    get_verification_provider,
)
from app.services.email_governance import email_hash, mask_email, normalize_email

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def score_candidate(
    row: ContactProviderCandidate,
    policy: ContactPersonaPolicy,
    *,
    product_interest_score: int = 0,
) -> tuple[int, list[str]]:
    """Return an explainable 0-100 ForgeBase relevance score."""

    title = (row.job_title or "").lower()
    department = (row.department or "").lower()
    seniority = (row.seniority or "").lower()
    location = (row.location or "").lower()
    excluded = [value.lower() for value in policy.excluded_title_terms]
    if any(term and term in title for term in excluded):
        return 0, ["excluded_title"]

    score = 15
    reasons = ["confirmed_company_domain"]
    if any(term.lower() in title for term in policy.target_titles):
        score += 35
        reasons.append("target_title")
    if any(term.lower() in department for term in policy.target_departments):
        score += 25
        reasons.append("target_department")
    if any(term.lower() in seniority for term in policy.target_seniorities):
        score += 15
        reasons.append("target_seniority")
    if any(term.lower() in location for term in policy.target_locations):
        score += 5
        reasons.append("target_location")
    if product_interest_score > 0:
        score += 5
        reasons.append("company_journey_product_interest")
    return min(score, 100), reasons


async def today_contact_usage(db, tenant_id: uuid.UUID) -> tuple[int, Decimal]:
    now = utcnow_naive()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    row = (
        await db.exec(
            select(
                func.count(ProviderUsage.id).filter(
                    ProviderUsage.operation == "contact_search"
                ),
                func.coalesce(func.sum(ProviderUsage.estimated_cost), 0),
            ).where(
                ProviderUsage.tenant_id == tenant_id,
                ProviderUsage.operation.in_(["contact_search", "email_verify"]),
                ProviderUsage.created_at >= start,
            )
        )
    ).one()
    return int(row[0]), Decimal(str(row[1]))


async def _provider_circuit_is_open(
    db,
    *,
    tenant_id: uuid.UUID,
    provider: str,
    operation: str,
) -> bool:
    from app.core.config import settings

    failure_limit = max(1, settings.CONTACT_PROVIDER_CIRCUIT_FAILURES)
    since = utcnow_naive() - timedelta(
        seconds=max(1, settings.CONTACT_PROVIDER_CIRCUIT_COOLDOWN_SECONDS)
    )
    statuses = list(
        (
            await db.exec(
                select(ProviderUsage.response_status)
                .where(
                    ProviderUsage.tenant_id == tenant_id,
                    ProviderUsage.provider == provider,
                    ProviderUsage.operation == operation,
                    ProviderUsage.created_at >= since,
                )
                .order_by(col(ProviderUsage.created_at).desc())
                .limit(failure_limit)
            )
        ).all()
    )
    return len(statuses) >= failure_limit and all(value == "error" for value in statuses)


async def _record_failed_attempt(
    *,
    context: ContactSearchContext,
    search_result: ContactSearchResult | None,
    search_latency_ms: int,
    verified_rows: list[
        tuple[ContactProviderCandidate, EmailVerificationResult, int]
    ],
    failed_provider: str,
    failed_operation: str,
    failed_request_key: str,
    failed_latency_ms: int,
    error: Exception,
    retry_count: int,
) -> None:
    """Persist cost/reliability evidence without provider payload or email."""

    async with get_session_ctx() as db:
        if search_result is not None:
            db.add(
                ProviderUsage(
                    tenant_id=context.tenant_id,
                    provider=search_result.provider,
                    operation="contact_search",
                    request_key=str(context.company_identification_id),
                    provider_request_id=search_result.request_id,
                    response_status=(
                        "matched" if search_result.candidates else "no_usable_match"
                    ),
                    latency_ms=search_latency_ms,
                    units=search_result.units,
                    estimated_cost=search_result.estimated_cost,
                    retry_count=max(0, retry_count),
                )
            )
        for row, verification, latency_ms in verified_rows:
            digest = email_hash(normalize_email(row.business_email))
            db.add(
                ProviderUsage(
                    tenant_id=context.tenant_id,
                    provider=verification.provider,
                    operation="email_verify",
                    request_key=f"candidate:{digest[:12]}",
                    provider_request_id=verification.request_id,
                    response_status=verification.status,
                    latency_ms=latency_ms,
                    units=verification.units,
                    estimated_cost=verification.estimated_cost,
                    retry_count=max(0, retry_count),
                )
            )
        db.add(
            ProviderUsage(
                tenant_id=context.tenant_id,
                provider=failed_provider,
                operation=failed_operation,
                request_key=failed_request_key,
                response_status="error",
                latency_ms=failed_latency_ms,
                error_class=type(error).__name__,
                retry_count=max(0, retry_count),
            )
        )
        await db.commit()


async def run_contact_enrichment_job(
    company_identification_id: uuid.UUID,
    *,
    retry_count: int = 0,
) -> int:
    """Find and verify review-only candidates for one confirmed company."""

    async with get_session_ctx() as db:
        company = (
            await db.exec(
                select(CompanyIdentification)
                .where(CompanyIdentification.id == company_identification_id)
                .with_for_update()
            )
        ).first()
        if not company:
            raise ContactProviderPermanentError("Company identification does not exist")
        policy = await db.get(ContactPersonaPolicy, company.tenant_id)
        now = utcnow_naive()
        if not policy or policy.mode != "review_only":
            return 0
        if company.status != "confirmed" or company.expires_at <= now or not company.domain:
            raise ContactProviderPermanentError("Only a current confirmed company with a domain can be enriched")
        if not (policy.target_departments or policy.target_titles):
            raise ContactProviderPermanentError("Persona policy requires target departments or titles")

        await db.exec(
            delete(ContactCandidate).where(
                ContactCandidate.tenant_id == company.tenant_id,
                ContactCandidate.company_identification_id == company.id,
                ContactCandidate.expires_at <= now,
                ContactCandidate.status != "converted",
            )
        )
        await db.commit()

        existing = (
            await db.exec(
                select(ContactCandidate.id).where(
                    ContactCandidate.tenant_id == company.tenant_id,
                    ContactCandidate.company_identification_id == company.id,
                    ContactCandidate.expires_at > now,
                )
            )
        ).first()
        if existing:
            return 0
        lookup_count, cost = await today_contact_usage(db, company.tenant_id)
        if lookup_count >= policy.daily_lookup_quota:
            raise ContactProviderPermanentError("Tenant contact lookup quota is exhausted")
        search_provider = get_contact_provider(policy.contact_provider_name)
        verifier = get_verification_provider(policy.verification_provider_name)
        from app.core.config import settings

        circuit_open = await _provider_circuit_is_open(
            db,
            tenant_id=company.tenant_id,
            provider=search_provider.name,
            operation="contact_search",
        ) or await _provider_circuit_is_open(
            db,
            tenant_id=company.tenant_id,
            provider=verifier.name,
            operation="email_verify",
        )
        if circuit_open:
            from app.services.contact_enrichment.providers import (
                ContactProviderRetryableError,
            )

            raise ContactProviderRetryableError(
                "Contact provider circuit is open",
                retry_after_seconds=max(
                    1, settings.CONTACT_PROVIDER_CIRCUIT_COOLDOWN_SECONDS
                ),
            )
        projected = search_provider.estimate_cost() + verifier.estimate_cost() * policy.max_candidates_per_company
        if cost + projected > policy.daily_provider_cost_limit:
            raise ContactProviderPermanentError("Tenant contact provider cost limit would be exceeded")
        visitor = await db.get(Visitor, company.visitor_id)
        product_interest = visitor.total_page_views if visitor else 0
        context = ContactSearchContext(
            tenant_id=company.tenant_id,
            company_identification_id=company.id,
            company_name=company.company_name,
            company_domain=company.domain.lower(),
            target_departments=tuple(policy.target_departments),
            target_titles=tuple(policy.target_titles),
            target_seniorities=tuple(policy.target_seniorities),
            target_locations=tuple(policy.target_locations),
            limit=policy.max_candidates_per_company,
        )

    # External calls happen outside the transaction and never receive visitor
    # identity or journey URLs.
    started = time.perf_counter()
    try:
        search_result = await search_provider.search(context)
    except Exception as exc:
        search_latency_ms = max(0, round((time.perf_counter() - started) * 1000))
        await _record_failed_attempt(
            context=context,
            search_result=None,
            search_latency_ms=0,
            verified_rows=[],
            failed_provider=search_provider.name,
            failed_operation="contact_search",
            failed_request_key=str(context.company_identification_id),
            failed_latency_ms=search_latency_ms,
            error=exc,
            retry_count=retry_count,
        )
        raise
    search_latency_ms = max(0, round((time.perf_counter() - started) * 1000))
    verified_rows: list[
        tuple[ContactProviderCandidate, EmailVerificationResult, int]
    ] = []
    for row in search_result.candidates:
        address = normalize_email(row.business_email)
        _, separator, domain = address.partition("@")
        if not separator or not _EMAIL_RE.fullmatch(address) or domain != context.company_domain:
            continue
        started = time.perf_counter()
        try:
            verification = await verifier.verify(address)
        except Exception as exc:
            verification_latency_ms = max(
                0, round((time.perf_counter() - started) * 1000)
            )
            await _record_failed_attempt(
                context=context,
                search_result=search_result,
                search_latency_ms=search_latency_ms,
                verified_rows=verified_rows,
                failed_provider=verifier.name,
                failed_operation="email_verify",
                failed_request_key=f"candidate:{email_hash(address)[:12]}",
                failed_latency_ms=verification_latency_ms,
                error=exc,
                retry_count=retry_count,
            )
            raise
        verification_latency_ms = max(
            0, round((time.perf_counter() - started) * 1000)
        )
        verified_rows.append((row, verification, verification_latency_ms))

    async with get_session_ctx() as db:
        company = (
            await db.exec(
                select(CompanyIdentification)
                .where(CompanyIdentification.id == company_identification_id)
                .with_for_update()
            )
        ).first()
        policy = await db.get(ContactPersonaPolicy, context.tenant_id)
        now = utcnow_naive()
        actual_cost = search_result.estimated_cost + sum(
            (result.estimated_cost for _, result, _ in verified_rows), Decimal(0)
        )
        db.add(
            ProviderUsage(
                tenant_id=context.tenant_id,
                provider=search_result.provider,
                operation="contact_search",
                request_key=str(context.company_identification_id),
                provider_request_id=search_result.request_id,
                response_status="matched" if verified_rows else "no_usable_match",
                latency_ms=search_latency_ms,
                units=search_result.units,
                estimated_cost=search_result.estimated_cost,
                retry_count=max(0, retry_count),
            )
        )
        for verified_row, verification, verification_latency_ms in verified_rows:
            digest = email_hash(normalize_email(verified_row.business_email))
            db.add(
                ProviderUsage(
                    tenant_id=context.tenant_id,
                    provider=verification.provider,
                    operation="email_verify",
                    request_key=f"candidate:{digest[:12]}",
                    provider_request_id=verification.request_id,
                    response_status=verification.status,
                    latency_ms=verification_latency_ms,
                    units=verification.units,
                    estimated_cost=verification.estimated_cost,
                    retry_count=max(0, retry_count),
                )
            )

        # Consent/policy/company state can change while the provider is called.
        # Usage is still committed because the external cost already occurred.
        if not company or not policy or policy.mode != "review_only" or company.status != "confirmed" or company.expires_at <= now:
            await db.commit()
            return 0
        lookup_count, cost = await today_contact_usage(db, context.tenant_id)
        # Exclude the just-staged usage: queries do not autoflush in every
        # SQLModel session configuration, while actual_cost is explicit.
        prior_cost = max(Decimal(0), cost - actual_cost)
        if lookup_count > policy.daily_lookup_quota or prior_cost + actual_cost > policy.daily_provider_cost_limit:
            await db.commit()
            raise ContactProviderPermanentError("Tenant provider guard changed while lookup was running")

        created = 0
        expires_at = min(
            now + timedelta(days=policy.candidate_retention_days),
            company.expires_at,
        )
        for row, verification, verification_latency_ms in verified_rows:
            address = normalize_email(row.business_email)
            digest = email_hash(address)
            duplicate = (
                await db.exec(
                    select(ContactCandidate.id).where(
                        ContactCandidate.tenant_id == context.tenant_id,
                        ContactCandidate.company_identification_id == company.id,
                        ContactCandidate.email_hash == digest,
                    )
                )
            ).first()
            if duplicate:
                continue
            globally_suppressed = (
                await db.exec(
                    select(EmailSuppression.id).where(
                        EmailSuppression.scope_key == "global",
                        EmailSuppression.email_hash == digest,
                        EmailSuppression.active.is_(True),
                    )
                )
            ).first()
            tenant_dnc = (
                await db.exec(
                    select(ContactCandidate.id).where(
                        ContactCandidate.tenant_id == context.tenant_id,
                        ContactCandidate.email_hash == digest,
                        ContactCandidate.status == ContactCandidateStatus.do_not_contact.value,
                    )
                )
            ).first()
            relevance, reasons = score_candidate(
                row, policy, product_interest_score=product_interest
            )
            status = (
                ContactCandidateStatus.do_not_contact.value
                if globally_suppressed or tenant_dnc
                else ContactCandidateStatus.candidate.value
            )
            is_dnc = status == ContactCandidateStatus.do_not_contact.value
            db.add(
                ContactCandidate(
                    tenant_id=context.tenant_id,
                    company_identification_id=company.id,
                    source_company_name=company.company_name,
                    source_company_domain=company.domain,
                    full_name="Suppressed business contact" if is_dnc else row.full_name.strip(),
                    job_title=None if is_dnc else (row.job_title or "").strip() or None,
                    department=None if is_dnc else (row.department or "").strip() or None,
                    seniority=None if is_dnc else (row.seniority or "").strip() or None,
                    location=None if is_dnc else (row.location or "").strip() or None,
                    email_ciphertext="" if is_dnc else encrypt(address),
                    email_hash=digest,
                    email_masked=mask_email(address),
                    verification_status=verification.status,
                    verification_provider=verification.provider,
                    verified_at=verification.checked_at,
                    source_provider=search_result.provider,
                    source_person_id=row.provider_person_id,
                    source_url=None if is_dnc else row.source_url,
                    source_freshness=row.source_freshness,
                    relevance_score=relevance,
                    relevance_reasons=reasons,
                    confidence=row.provider_confidence,
                    status=status,
                    created_at=now,
                    updated_at=now,
                    expires_at=expires_at,
                )
            )
            created += 1
        await db.commit()
        return created


async def purge_expired_contact_candidates(db) -> int:
    """Delete expired, unconverted candidate PII at the configured TTL."""

    now = utcnow_naive()
    result = await db.exec(
        delete(ContactCandidate).where(
            ContactCandidate.expires_at <= now,
            ContactCandidate.status != "converted",
            ~select(OutreachMessage.id)
            .where(OutreachMessage.contact_candidate_id == ContactCandidate.id)
            .exists(),
        )
    )
    return int(result.rowcount or 0)
