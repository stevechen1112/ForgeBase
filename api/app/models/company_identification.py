"""Company-identification foundation models.

These records intentionally describe inferred companies, never a visitor's
personal identity.  Raw IP addresses are not duplicated into this domain;
``NetworkObservation`` stores only privacy-minimised lookup evidence and a
reference to the originating tracking event.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class NetworkEligibilityStatus(str, Enum):
    pending = "pending"
    eligible = "eligible"
    ineligible = "ineligible"
    expired = "expired"


class IdentificationStatus(str, Enum):
    shadow = "shadow"
    candidate = "candidate"
    confirmed = "confirmed"
    rejected = "rejected"
    expired = "expired"
    conflict = "conflict"


class IdentificationReviewDecision(str, Enum):
    confirm = "confirm"
    reject = "reject"
    correct = "correct"


class ConfidenceBand(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class CompanyIdentificationMode(str, Enum):
    off = "off"
    shadow = "shadow"
    review_only = "review_only"
    approval_send = "approval_send"
    controlled_auto = "controlled_auto"


class GrowthAutomationPolicy(SQLModel, table=True):
    """Platform-controlled tenant policy for staged North Star capabilities."""

    __tablename__ = "growth_automation_policies"
    __table_args__ = (
        CheckConstraint(
            "company_identification_mode IN "
            "('off', 'shadow', 'review_only', 'approval_send', 'controlled_auto')",
            name="ck_growth_policy_company_identification_mode",
        ),
        CheckConstraint("min_intent_score >= 0", name="ck_growth_policy_min_intent_score"),
        CheckConstraint(
            "observation_retention_days >= 1 AND observation_retention_days <= 365",
            name="ck_growth_policy_observation_retention",
        ),
        CheckConstraint("daily_lookup_quota >= 0", name="ck_growth_policy_daily_lookup_quota"),
        CheckConstraint(
            "daily_provider_cost_limit >= 0",
            name="ck_growth_policy_daily_provider_cost_limit",
        ),
        CheckConstraint(
            "medium_confidence_threshold >= 0 AND medium_confidence_threshold <= 1",
            name="ck_growth_policy_medium_confidence",
        ),
        CheckConstraint(
            "high_confidence_threshold >= 0 AND high_confidence_threshold <= 1",
            name="ck_growth_policy_high_confidence",
        ),
        CheckConstraint(
            "high_confidence_threshold >= medium_confidence_threshold",
            name="ck_growth_policy_confidence_order",
        ),
    )

    tenant_id: uuid.UUID = Field(primary_key=True, foreign_key="tenants.id", ondelete="CASCADE")
    company_identification_mode: str = Field(
        default=CompanyIdentificationMode.off.value,
        max_length=30,
        index=True,
    )
    provider_name: str = Field(default="mock", max_length=50)
    min_intent_score: int = Field(default=40, ge=0)
    observation_retention_days: int = Field(default=30, ge=1, le=365)
    daily_lookup_quota: int = Field(default=100, ge=0)
    daily_provider_cost_limit: Decimal = Field(
        default=Decimal(10),
        sa_column=Column(Numeric(14, 6), nullable=False, default=Decimal(10)),
    )
    medium_confidence_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    high_confidence_threshold: float = Field(default=0.90, ge=0.0, le=1.0)
    allowed_countries: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=list),
    )
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class NetworkObservation(SQLModel, table=True):
    """Privacy-minimised network evidence eligible for company lookup."""

    __tablename__ = "network_observations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "dedupe_key",
            name="uq_network_observation_tenant_dedupe",
        ),
        CheckConstraint("ip_version IN (4, 6)", name="ck_network_observation_ip_version"),
        CheckConstraint(
            "eligibility_status IN ('pending', 'eligible', 'ineligible', 'expired')",
            name="ck_network_observation_eligibility_status",
        ),
        CheckConstraint("expires_at > observed_at", name="ck_network_observation_expiry"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", ondelete="CASCADE", index=True)
    visitor_id: uuid.UUID = Field(foreign_key="visitors.visitor_id", ondelete="CASCADE", index=True)
    session_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="tracking_sessions.session_id",
        ondelete="SET NULL",
        index=True,
    )
    source_event_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="tracking_events.event_id",
        ondelete="SET NULL",
        index=True,
    )

    # Never add a raw-IP column here.  Provider runtimes must retrieve the
    # source value transiently and keep OperationalJob payloads IP-free.
    ip_hash: str = Field(max_length=64, index=True)
    ip_masked: str = Field(max_length=64)
    ip_version: int = Field(ge=4, le=6)
    ip_source: str = Field(default="request", max_length=30)

    is_private: bool = Field(default=False)
    is_bot: bool = Field(default=False)
    is_vpn: bool = Field(default=False)
    is_proxy: bool = Field(default=False)
    is_hosting: bool = Field(default=False)
    eligibility_status: str = Field(
        default=NetworkEligibilityStatus.pending.value,
        max_length=20,
        index=True,
    )
    ineligible_reason: str | None = Field(default=None, max_length=100)

    country: str | None = Field(default=None, max_length=2)
    asn: str | None = Field(default=None, max_length=30)
    asn_org: str | None = Field(default=None, max_length=300)
    consent_state: str = Field(default="unknown", max_length=20, index=True)
    policy_version: str = Field(max_length=40)
    dedupe_key: str = Field(max_length=160)

    observed_at: datetime = Field(default_factory=utcnow_naive, index=True)
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow_naive)


class CompanyIdentification(SQLModel, table=True):
    """One provider's evidence-backed company candidate for a visitor."""

    __tablename__ = "company_identifications"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "network_observation_id",
            "provider",
            "candidate_key",
            name="uq_company_identification_provider_candidate",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_company_identification_confidence",
        ),
        CheckConstraint(
            "confidence_band IN ('low', 'medium', 'high')",
            name="ck_company_identification_confidence_band",
        ),
        CheckConstraint(
            "status IN ('shadow', 'candidate', 'confirmed', 'rejected', 'expired', 'conflict')",
            name="ck_company_identification_status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", ondelete="CASCADE", index=True)
    visitor_id: uuid.UUID = Field(foreign_key="visitors.visitor_id", ondelete="CASCADE", index=True)
    network_observation_id: uuid.UUID = Field(
        foreign_key="network_observations.id",
        ondelete="CASCADE",
        index=True,
    )

    company_name: str = Field(max_length=300)
    domain: str | None = Field(default=None, max_length=253, index=True)
    provider_company_id: str | None = Field(default=None, max_length=200)
    provider: str = Field(max_length=50, index=True)
    candidate_key: str = Field(max_length=300)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_band: str = Field(max_length=20, index=True)
    evidence_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False, default=dict),
    )
    match_method: str = Field(max_length=50)
    source_freshness: datetime | None = Field(default=None)
    status: str = Field(
        default=IdentificationStatus.shadow.value,
        max_length=20,
        index=True,
    )

    reviewed_by: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    reviewed_at: datetime | None = Field(default=None)
    review_note: str | None = Field(default=None, max_length=2000)
    expires_at: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class IdentificationReview(SQLModel, table=True):
    """Append-only human decision used for audit and quality feedback."""

    __tablename__ = "identification_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('confirm', 'reject', 'correct')",
            name="ck_identification_review_decision",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", ondelete="CASCADE", index=True)
    company_identification_id: uuid.UUID = Field(
        foreign_key="company_identifications.id",
        ondelete="CASCADE",
        index=True,
    )
    decision: str = Field(max_length=20, index=True)
    corrected_company_name: str | None = Field(default=None, max_length=300)
    corrected_domain: str | None = Field(default=None, max_length=253)
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    reviewed_by: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL", index=True)
    reviewed_at: datetime = Field(default_factory=utcnow_naive, index=True)


class ProviderUsage(SQLModel, table=True):
    """Cost and reliability ledger for external growth-data operations."""

    __tablename__ = "provider_usage"
    __table_args__ = (
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_provider_usage_latency"),
        CheckConstraint("units >= 0", name="ck_provider_usage_units"),
        CheckConstraint("estimated_cost >= 0", name="ck_provider_usage_estimated_cost"),
        CheckConstraint("retry_count >= 0", name="ck_provider_usage_retry_count"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", ondelete="CASCADE", index=True)
    provider: str = Field(max_length=50, index=True)
    operation: str = Field(max_length=50, index=True)
    request_key: str = Field(max_length=200, index=True)
    provider_request_id: str | None = Field(default=None, max_length=300)
    response_status: str = Field(max_length=40, index=True)
    latency_ms: int | None = Field(default=None, ge=0)
    units: int = Field(default=0, ge=0)
    estimated_cost: Decimal = Field(
        default=Decimal(0),
        sa_column=Column(Numeric(14, 6), nullable=False, default=Decimal(0)),
    )
    cache_hit: bool = Field(default=False, index=True)
    error_class: str | None = Field(default=None, max_length=100)
    retry_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
