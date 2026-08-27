"""Tenant-scoped North Star lineage and attribution decision history."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class AttributionLink(SQLModel, table=True):
    """Current, evidence-backed attribution for one RFQ."""

    __tablename__ = "attribution_links"
    __table_args__ = (
        UniqueConstraint("rfq_request_id", name="uq_attribution_link_rfq"),
        CheckConstraint(
            "attribution_type IN ('direct', 'assisted', 'unknown', 'manual')",
            name="ck_attribution_link_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_attribution_link_confidence",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    rfq_request_id: uuid.UUID = Field(
        foreign_key="rfq_requests.id", ondelete="CASCADE", index=True
    )
    visitor_id: uuid.UUID | None = Field(
        default=None, foreign_key="visitors.visitor_id", ondelete="SET NULL", index=True
    )
    company_identification_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="company_identifications.id",
        ondelete="SET NULL",
        index=True,
    )
    contact_candidate_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="contact_candidates.id",
        ondelete="SET NULL",
        index=True,
    )
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contacts.id", ondelete="SET NULL", index=True
    )
    journey_snapshot_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="journey_snapshots.id",
        ondelete="SET NULL",
        index=True,
    )
    outreach_message_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="outreach_messages.id",
        ondelete="SET NULL",
        index=True,
    )
    inbound_reply_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="inbound_replies.id",
        ondelete="SET NULL",
        index=True,
    )
    sales_handoff_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="sales_handoffs.id",
        ondelete="SET NULL",
        index=True,
    )
    attribution_type: str = Field(default="unknown", max_length=20, index=True)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    derivation_version: str = Field(default="north-star-attribution-v1", max_length=80)
    manually_overridden: bool = Field(default=False, index=True)
    override_reason: str | None = Field(default=None, max_length=2000)
    overridden_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )
    overridden_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive, index=True)


class AttributionEvent(SQLModel, table=True):
    """Append-only derivation, override and RFQ outcome audit."""

    __tablename__ = "attribution_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('derived', 'recalculated', 'manual_override', 'outcome_changed')",
            name="ck_attribution_event_action",
        ),
        CheckConstraint(
            "previous_type IS NULL OR previous_type IN "
            "('direct', 'assisted', 'unknown', 'manual')",
            name="ck_attribution_event_previous_type",
        ),
        CheckConstraint(
            "attribution_type IN ('direct', 'assisted', 'unknown', 'manual')",
            name="ck_attribution_event_type",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_attribution_event_confidence",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    attribution_link_id: uuid.UUID = Field(
        foreign_key="attribution_links.id", ondelete="CASCADE", index=True
    )
    rfq_request_id: uuid.UUID = Field(
        foreign_key="rfq_requests.id", ondelete="CASCADE", index=True
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )
    action: str = Field(max_length=30, index=True)
    previous_type: str | None = Field(default=None, max_length=20)
    attribution_type: str = Field(max_length=20, index=True)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str | None = Field(default=None, max_length=2000)
    evidence: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
