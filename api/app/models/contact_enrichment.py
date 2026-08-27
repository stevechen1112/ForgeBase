"""Company-related contact candidates and their human-review policy.

A candidate is a possible business contact at an inferred company.  It is
never evidence that the person was the anonymous visitor.  Candidate email
addresses are encrypted at rest; normal APIs expose only the masked value.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, Column, Numeric, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ContactEnrichmentMode(str, Enum):
    off = "off"
    review_only = "review_only"


class EmailVerificationStatus(str, Enum):
    verified = "verified"
    risky = "risky"
    catch_all = "catch_all"
    unknown = "unknown"
    invalid = "invalid"


class ContactCandidateStatus(str, Enum):
    candidate = "candidate"
    approved = "approved"
    rejected = "rejected"
    converted = "converted"
    expired = "expired"
    do_not_contact = "do_not_contact"


class ContactCandidateDecision(str, Enum):
    approve = "approve"
    reject = "reject"
    convert = "convert"
    do_not_contact = "do_not_contact"


class ContactPersonaPolicy(SQLModel, table=True):
    """Tenant-scoped limits for a narrow, review-only candidate search."""

    __tablename__ = "contact_persona_policies"
    __table_args__ = (
        CheckConstraint("mode IN ('off', 'review_only')", name="ck_contact_persona_mode"),
        CheckConstraint(
            "min_relevance_score >= 0 AND min_relevance_score <= 100",
            name="ck_contact_persona_min_relevance",
        ),
        CheckConstraint(
            "candidate_retention_days >= 1 AND candidate_retention_days <= 365",
            name="ck_contact_persona_retention",
        ),
        CheckConstraint(
            "max_candidates_per_company >= 1 AND max_candidates_per_company <= 25",
            name="ck_contact_persona_max_candidates",
        ),
        CheckConstraint("daily_lookup_quota >= 0", name="ck_contact_persona_daily_quota"),
        CheckConstraint(
            "daily_provider_cost_limit >= 0",
            name="ck_contact_persona_daily_cost",
        ),
    )

    tenant_id: uuid.UUID = Field(primary_key=True, foreign_key="tenants.id", ondelete="CASCADE")
    mode: str = Field(default=ContactEnrichmentMode.off.value, max_length=20, index=True)
    contact_provider_name: str = Field(default="mock", max_length=50)
    verification_provider_name: str = Field(default="mock", max_length=50)
    target_departments: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    target_titles: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    target_seniorities: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    target_locations: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    excluded_title_terms: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    min_relevance_score: int = Field(default=60, ge=0, le=100)
    candidate_retention_days: int = Field(default=90, ge=1, le=365)
    max_candidates_per_company: int = Field(default=5, ge=1, le=25)
    daily_lookup_quota: int = Field(default=25, ge=0)
    daily_provider_cost_limit: Decimal = Field(
        default=Decimal(5),
        sa_column=Column(Numeric(14, 6), nullable=False, default=Decimal(5)),
    )
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class ContactCandidate(SQLModel, table=True):
    """Privacy-minimised, evidence-backed business contact candidate."""

    __tablename__ = "contact_candidates"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "company_identification_id",
            "email_hash",
            name="uq_contact_candidate_company_email",
        ),
        CheckConstraint(
            "verification_status IN ('verified', 'risky', 'catch_all', 'unknown', 'invalid')",
            name="ck_contact_candidate_verification",
        ),
        CheckConstraint(
            "status IN ('candidate', 'approved', 'rejected', 'converted', 'expired', 'do_not_contact')",
            name="ck_contact_candidate_status",
        ),
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 100",
            name="ck_contact_candidate_relevance",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_contact_candidate_confidence",
        ),
        CheckConstraint("expires_at > created_at", name="ck_contact_candidate_expiry"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", ondelete="CASCADE", index=True)
    company_identification_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="company_identifications.id",
        ondelete="SET NULL",
        index=True,
    )

    source_company_name: str = Field(max_length=300)
    source_company_domain: str = Field(max_length=253)

    full_name: str = Field(max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    department: str | None = Field(default=None, max_length=100)
    seniority: str | None = Field(default=None, max_length=80)
    location: str | None = Field(default=None, max_length=200)

    email_ciphertext: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    email_hash: str = Field(max_length=64, index=True, repr=False)
    email_masked: str = Field(max_length=254)
    verification_status: str = Field(
        default=EmailVerificationStatus.unknown.value, max_length=20, index=True
    )
    verification_provider: str | None = Field(default=None, max_length=50)
    verified_at: datetime | None = Field(default=None)

    source_provider: str = Field(max_length=50, index=True)
    source_person_id: str | None = Field(default=None, max_length=200)
    source_url: str | None = Field(default=None, max_length=1000)
    source_freshness: datetime | None = Field(default=None)
    relevance_score: int = Field(ge=0, le=100, index=True)
    relevance_reasons: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(default=ContactCandidateStatus.candidate.value, max_length=20, index=True)

    reviewed_by: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    reviewed_at: datetime | None = Field(default=None)
    review_reason_code: str | None = Field(default=None, max_length=80)
    review_note: str | None = Field(default=None, max_length=2000)
    converted_contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contacts.id", ondelete="SET NULL", index=True
    )
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    expires_at: datetime = Field(index=True)


class ContactCandidateReview(SQLModel, table=True):
    """Append-only reviewer decision and conversion provenance."""

    __tablename__ = "contact_candidate_reviews"
    __table_args__ = (
        CheckConstraint(
            "decision IN ('approve', 'reject', 'convert', 'do_not_contact')",
            name="ck_contact_candidate_review_decision",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", ondelete="CASCADE", index=True)
    contact_candidate_id: uuid.UUID = Field(
        foreign_key="contact_candidates.id", ondelete="CASCADE", index=True
    )
    decision: str = Field(max_length=30, index=True)
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    reviewer_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", ondelete="SET NULL")
    resulting_contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contacts.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
