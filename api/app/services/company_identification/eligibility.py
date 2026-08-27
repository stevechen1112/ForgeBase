"""Network eligibility and observation creation for Shadow Mode."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.models.company_identification import (
    CompanyIdentificationMode,
    GrowthAutomationPolicy,
    NetworkEligibilityStatus,
    NetworkObservation,
)
from app.models.tracking_event import TrackingEvent
from app.models.visitor import Visitor
from app.services.company_identification.jobs import enqueue_company_identification_job

_BOT_PATTERN = re.compile(
    r"bot|crawler|spider|slurp|headless|preview|facebookexternalhit|linkedinbot",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class NetworkAssessment:
    ip_version: int
    ip_masked: str
    is_private: bool
    is_bot: bool
    eligible: bool
    ineligible_reason: str | None = None


def assess_network(ip_address: str, user_agent: str | None = None) -> NetworkAssessment:
    try:
        address = ipaddress.ip_address(ip_address)
    except ValueError as exc:
        raise ValueError("invalid IP address") from exc

    prefix = 24 if address.version == 4 else 48
    masked = str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))
    is_private = not address.is_global
    is_bot = bool(_BOT_PATTERN.search(user_agent or ""))
    reason = "non_public_network" if is_private else "bot" if is_bot else None
    return NetworkAssessment(
        ip_version=address.version,
        ip_masked=masked,
        is_private=is_private,
        is_bot=is_bot,
        eligible=reason is None,
        ineligible_reason=reason,
    )


def hash_network_identifier(tenant_id: uuid.UUID, ip_address: str) -> str:
    message = f"{tenant_id}:{ip_address}".encode()
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


async def maybe_create_network_observation(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    visitor: Visitor,
    source_event: TrackingEvent,
    client_ip: str | None,
    analytics_consent: bool,
    user_agent: str | None,
) -> NetworkObservation | None:
    """Create one daily observation and queue an eligible Shadow lookup."""

    policy = (
        await db.exec(
            select(GrowthAutomationPolicy)
            .where(GrowthAutomationPolicy.tenant_id == tenant_id)
            .with_for_update()
        )
    ).first()
    if not policy or policy.company_identification_mode == CompanyIdentificationMode.off.value:
        return None
    if not analytics_consent or visitor.analytics_consent_status == "denied":
        return None
    if visitor.intent_score < policy.min_intent_score or not client_ip:
        return None

    try:
        assessment = assess_network(client_ip, user_agent)
    except ValueError:
        return None

    now = utcnow_naive()
    ip_hash = hash_network_identifier(tenant_id, client_ip)
    dedupe_material = f"{tenant_id}:{visitor.visitor_id}:{ip_hash}:{now.date().isoformat()}"
    dedupe_key = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        dedupe_material.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    existing = (
        await db.exec(
            select(NetworkObservation).where(
                NetworkObservation.tenant_id == tenant_id,
                NetworkObservation.dedupe_key == dedupe_key,
            )
        )
    ).first()
    if existing:
        return existing

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    eligible_today = (
        await db.exec(
            select(func.count(NetworkObservation.id)).where(
                NetworkObservation.tenant_id == tenant_id,
                NetworkObservation.eligibility_status == NetworkEligibilityStatus.eligible.value,
                NetworkObservation.observed_at >= start_of_day,
            )
        )
    ).one()

    normalized_country = (source_event.country or "").strip().upper() or None
    country_allowed = not policy.allowed_countries or normalized_country in policy.allowed_countries
    eligible = (
        assessment.eligible
        and country_allowed
        and eligible_today < policy.daily_lookup_quota
    )
    reason = assessment.ineligible_reason
    if assessment.eligible and not country_allowed:
        reason = "country_not_allowed"
    elif assessment.eligible and not eligible:
        reason = "daily_quota_exceeded"

    observation = NetworkObservation(
        tenant_id=tenant_id,
        visitor_id=visitor.visitor_id,
        session_id=source_event.session_id,
        source_event_id=source_event.event_id,
        ip_hash=ip_hash,
        ip_masked=assessment.ip_masked,
        ip_version=assessment.ip_version,
        ip_source="trusted_request_chain",
        is_private=assessment.is_private,
        is_bot=assessment.is_bot,
        eligibility_status=(
            NetworkEligibilityStatus.eligible.value
            if eligible
            else NetworkEligibilityStatus.ineligible.value
        ),
        ineligible_reason=reason,
        country=normalized_country,
        consent_state="granted",
        policy_version=settings.CONSENT_POLICY_VERSION,
        dedupe_key=dedupe_key,
        observed_at=now,
        expires_at=now + timedelta(days=policy.observation_retention_days),
    )
    try:
        async with db.begin_nested():
            db.add(observation)
            await db.flush()
    except IntegrityError:
        # A concurrent request may win the tenant/day dedupe race. Preserve
        # the outer event transaction and return the canonical observation.
        concurrent = (
            await db.exec(
                select(NetworkObservation).where(
                    NetworkObservation.tenant_id == tenant_id,
                    NetworkObservation.dedupe_key == dedupe_key,
                )
            )
        ).first()
        if concurrent:
            return concurrent
        raise
    if eligible:
        enqueue_company_identification_job(
            db,
            tenant_id=tenant_id,
            network_observation_id=observation.id,
        )
    return observation
