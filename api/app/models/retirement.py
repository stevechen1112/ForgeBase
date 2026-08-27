"""Evidence ledger for safe retirement of non-core feature candidates."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class RetirementCandidateObservation(SQLModel, table=True):
    """Persistent observation window and human decision for one candidate."""

    __tablename__ = "retirement_candidate_observations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('observing', 'retained', 'approved_removal', 'removed')",
            name="ck_retirement_candidate_status",
        ),
        CheckConstraint(
            "code_state IN ('active', 'disabled', 'removed')",
            name="ck_retirement_candidate_code_state",
        ),
        CheckConstraint(
            "required_observation_days >= 0",
            name="ck_retirement_candidate_days",
        ),
        CheckConstraint(
            "data_disposition IS NULL OR data_disposition IN "
            "('not_applicable', 'retained', 'exported', 'deleted')",
            name="ck_retirement_candidate_data_disposition",
        ),
    )

    candidate_key: str = Field(primary_key=True, max_length=80)
    display_name: str = Field(max_length=160)
    required_observation_days: int = Field(default=30, ge=0)
    code_state: str = Field(default="disabled", max_length=20, index=True)
    status: str = Field(default="observing", max_length=30, index=True)
    started_at: datetime = Field(default_factory=utcnow_naive, index=True)
    decided_at: datetime | None = Field(default=None)
    decided_by: uuid.UUID | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL",
        index=True,
    )
    decision_reason: str | None = Field(default=None, max_length=2000)
    telemetry_verified_at: datetime | None = Field(default=None)
    telemetry_verified_by: uuid.UUID | None = Field(
        default=None,
        foreign_key="users.id",
        ondelete="SET NULL",
        index=True,
    )
    telemetry_evidence_ref: str | None = Field(default=None, max_length=500)
    data_disposition: str | None = Field(default=None, max_length=30)
    rollback_revision: str | None = Field(default=None, max_length=100)
    removal_plan_ref: str | None = Field(default=None, max_length=500)
    updated_at: datetime = Field(default_factory=utcnow_naive, index=True)


class RetirementUsageEvent(SQLModel, table=True):
    """Minimal, PII-free evidence that a retirement candidate was used."""

    __tablename__ = "retirement_usage_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    candidate_key: str = Field(
        foreign_key="retirement_candidate_observations.candidate_key",
        ondelete="CASCADE",
        max_length=80,
        index=True,
    )
    tenant_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="tenants.id",
        ondelete="SET NULL",
        index=True,
    )
    event_name: str = Field(max_length=80, index=True)
    source: str = Field(max_length=40)
    occurred_at: datetime = Field(default_factory=utcnow_naive, index=True)
