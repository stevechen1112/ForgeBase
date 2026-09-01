"""Evidence-backed journey snapshots and controlled outreach delivery."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class OutreachDraftMode(str, Enum):
    off = "off"
    review_only = "review_only"


class OutreachMessageStatus(str, Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    queued = "queued"
    sending = "sending"
    sent = "sent"
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    bounced = "bounced"
    complained = "complained"
    unsubscribed = "unsubscribed"
    failed = "failed"


class OutreachDeliveryPolicy(SQLModel, table=True):
    """Tenant-scoped delivery limits plus a non-activating auto-readiness record."""

    __tablename__ = "outreach_delivery_policies"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('off', 'approval_send')", name="ck_outreach_delivery_policy_mode"
        ),
        CheckConstraint(
            "provider_name = 'resend'", name="ck_outreach_delivery_provider"
        ),
        CheckConstraint(
            "quiet_start_hour >= 0 AND quiet_start_hour <= 23",
            name="ck_outreach_quiet_start",
        ),
        CheckConstraint(
            "quiet_end_hour >= 0 AND quiet_end_hour <= 23", name="ck_outreach_quiet_end"
        ),
        CheckConstraint("daily_send_quota >= 0", name="ck_outreach_daily_send_quota"),
        CheckConstraint(
            "frequency_cap_days >= 1 AND frequency_cap_days <= 365",
            name="ck_outreach_frequency_days",
        ),
        CheckConstraint(
            "unsubscribe_scope IN ('tenant', 'global')",
            name="ck_outreach_unsubscribe_scope",
        ),
        CheckConstraint(
            "controlled_auto_review_sample_pct >= 1 AND "
            "controlled_auto_review_sample_pct <= 100",
            name="ck_outreach_auto_review_sample",
        ),
    )

    tenant_id: uuid.UUID = Field(
        primary_key=True, foreign_key="tenants.id", ondelete="CASCADE"
    )
    mode: str = Field(default="off", max_length=20, index=True)
    provider_name: str = Field(default="resend", max_length=20)
    timezone: str = Field(default="UTC", max_length=64)
    quiet_hours_enabled: bool = Field(default=True)
    quiet_start_hour: int = Field(default=20, ge=0, le=23)
    quiet_end_hour: int = Field(default=8, ge=0, le=23)
    daily_send_quota: int = Field(default=10, ge=0)
    frequency_cap_days: int = Field(default=30, ge=1, le=365)
    unsubscribe_scope: str = Field(default="tenant", max_length=20)
    controlled_auto_opt_in: bool = Field(default=False)
    controlled_auto_legal_approved: bool = Field(default=False)
    controlled_auto_allowed_regions: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    controlled_auto_allowed_personas: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    controlled_auto_allowed_templates: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    controlled_auto_review_sample_pct: int = Field(default=100, ge=1, le=100)
    controlled_auto_reviewed_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    controlled_auto_reviewed_at: datetime | None = Field(default=None)
    updated_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class OutreachDraftPolicy(SQLModel, table=True):
    __tablename__ = "outreach_draft_policies"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('off', 'review_only')", name="ck_outreach_policy_mode"
        ),
        CheckConstraint(
            "lookback_days >= 1 AND lookback_days <= 365",
            name="ck_outreach_policy_lookback",
        ),
        CheckConstraint(
            "snapshot_retention_days >= 1 AND snapshot_retention_days <= 365",
            name="ck_outreach_policy_retention",
        ),
        CheckConstraint(
            "max_evidence_events >= 1 AND max_evidence_events <= 500",
            name="ck_outreach_policy_max_events",
        ),
    )

    tenant_id: uuid.UUID = Field(
        primary_key=True, foreign_key="tenants.id", ondelete="CASCADE"
    )
    mode: str = Field(default=OutreachDraftMode.off.value, max_length=20, index=True)
    lookback_days: int = Field(default=30, ge=1, le=365)
    snapshot_retention_days: int = Field(default=90, ge=1, le=365)
    max_evidence_events: int = Field(default=100, ge=1, le=500)
    allowed_languages: list[str] = Field(
        default_factory=lambda: ["en", "zh-TW"],
        sa_column=Column(JSON, nullable=False, default=list),
    )
    policy_version: str = Field(default="outreach-review-v1", max_length=60)
    updated_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class JourneySnapshot(SQLModel, table=True):
    """Immutable, privacy-minimised evidence selected from valid first-party events."""

    __tablename__ = "journey_snapshots"
    __table_args__ = (
        UniqueConstraint("generation_key", name="uq_journey_snapshot_generation_key"),
        CheckConstraint("expires_at > generated_at", name="ck_journey_snapshot_expiry"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    visitor_id: uuid.UUID = Field(
        foreign_key="visitors.visitor_id", ondelete="CASCADE", index=True
    )
    company_identification_id: uuid.UUID = Field(
        foreign_key="company_identifications.id", ondelete="CASCADE", index=True
    )
    contact_candidate_id: uuid.UUID = Field(
        foreign_key="contact_candidates.id", ondelete="CASCADE", index=True
    )
    generation_key: str = Field(max_length=200, index=True)
    top_products: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    top_pages: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    downloads: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    comparisons: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    cta_signals: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    journey_signals: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    summary: str = Field(sa_column=Column(Text, nullable=False))
    evidence_event_ids: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    knowledge_references: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    policy_version: str = Field(max_length=60)
    generated_at: datetime = Field(default_factory=utcnow_naive, index=True)
    expires_at: datetime = Field(index=True)


class OutreachMessage(SQLModel, table=True):
    """Versioned draft plus immutable provider-submission snapshot."""

    __tablename__ = "outreach_messages"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "contact_candidate_id",
            "revision_no",
            name="uq_outreach_candidate_revision",
        ),
        UniqueConstraint(
            "send_idempotency_key", name="uq_outreach_messages_send_idempotency_key"
        ),
        UniqueConstraint(
            "provider", "provider_message_id", name="uq_outreach_provider_message"
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_review', 'approved', 'rejected', 'cancelled', "
            "'queued', 'sending', 'sent', 'delivered', 'opened', 'clicked', 'bounced', "
            "'replied', 'complained', 'unsubscribed', 'failed')",
            name="ck_outreach_message_status",
        ),
        CheckConstraint("revision_no >= 1", name="ck_outreach_message_revision"),
        CheckConstraint("send_attempts >= 0", name="ck_outreach_message_send_attempts"),
        CheckConstraint(
            "char_length(subject_snapshot) > 0", name="ck_outreach_subject_not_empty"
        ),
        CheckConstraint(
            "char_length(text_snapshot) > 0", name="ck_outreach_text_not_empty"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    visitor_id: uuid.UUID = Field(
        foreign_key="visitors.visitor_id", ondelete="CASCADE", index=True
    )
    company_identification_id: uuid.UUID = Field(
        foreign_key="company_identifications.id", ondelete="CASCADE", index=True
    )
    contact_candidate_id: uuid.UUID = Field(
        foreign_key="contact_candidates.id", ondelete="CASCADE", index=True
    )
    contact_id: uuid.UUID | None = Field(
        default=None, foreign_key="contacts.id", ondelete="SET NULL", index=True
    )
    journey_snapshot_id: uuid.UUID = Field(
        foreign_key="journey_snapshots.id", ondelete="CASCADE", index=True
    )
    nurture_sequence_id: uuid.UUID | None = Field(
        default=None, foreign_key="nurture_sequences.id", ondelete="SET NULL"
    )
    nurture_step_id: uuid.UUID | None = Field(
        default=None, foreign_key="nurture_steps.id", ondelete="SET NULL"
    )
    revision_of_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="outreach_messages.id",
        ondelete="SET NULL",
        index=True,
    )
    revision_no: int = Field(default=1, ge=1)

    purpose: str = Field(default="business_inquiry", max_length=50)
    channel: str = Field(default="email", max_length=20)
    language: str = Field(default="en", max_length=10)
    to_email_ciphertext: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    to_email_hash: str = Field(max_length=64, index=True, repr=False)
    to_email_masked: str = Field(max_length=254)
    subject_snapshot: str = Field(max_length=500)
    html_snapshot: str = Field(sa_column=Column(Text, nullable=False))
    text_snapshot: str = Field(sa_column=Column(Text, nullable=False))
    personalization_evidence: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    knowledge_version: str = Field(max_length=100)
    prompt_version: str = Field(max_length=80)
    policy_version: str = Field(max_length=80)
    generation_model: str = Field(max_length=100)
    content_hash: str = Field(max_length=64, index=True)
    status: str = Field(
        default=OutreachMessageStatus.pending_review.value, max_length=30, index=True
    )

    approved_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    approved_at: datetime | None = Field(default=None)
    rejected_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    rejected_at: datetime | None = Field(default=None)
    review_note: str | None = Field(default=None, max_length=2000)
    created_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    generated_at: datetime = Field(default_factory=utcnow_naive)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive, index=True)

    send_idempotency_key: str | None = Field(default=None, max_length=200)
    send_requested_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    send_requested_at: datetime | None = Field(default=None)
    scheduled_for: datetime | None = Field(default=None, index=True)
    send_attempts: int = Field(default=0, ge=0)
    sending_at: datetime | None = Field(default=None)
    provider: str | None = Field(default=None, max_length=20, index=True)
    provider_message_id: str | None = Field(default=None, max_length=120, index=True)
    sent_subject_snapshot: str | None = Field(default=None, max_length=500)
    sent_from_name: str | None = Field(default=None, max_length=200)
    sent_from_email: str | None = Field(default=None, max_length=254)
    sent_reply_to: str | None = Field(default=None, max_length=320)
    reply_route_token_hash: str | None = Field(
        default=None, max_length=64, unique=True, index=True, repr=False
    )
    sent_html_snapshot: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    sent_text_snapshot: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    sent_headers: dict[str, str] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    unsubscribe_token_hash: str | None = Field(
        default=None, max_length=64, index=True, repr=False
    )
    sent_at: datetime | None = Field(default=None, index=True)
    delivered_at: datetime | None = Field(default=None)
    opened_at: datetime | None = Field(default=None)
    clicked_at: datetime | None = Field(default=None)
    bounced_at: datetime | None = Field(default=None)
    complained_at: datetime | None = Field(default=None)
    unsubscribed_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=2000)


class OutreachMessageReview(SQLModel, table=True):
    """Append-only draft generation, revision and review audit."""

    __tablename__ = "outreach_message_reviews"
    __table_args__ = (
        CheckConstraint(
            "action IN ('generated', 'revised', 'approved', 'rejected', 'send_queued', "
            "'send_cancelled', 'send_retried')",
            name="ck_outreach_review_action",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    outreach_message_id: uuid.UUID = Field(
        foreign_key="outreach_messages.id", ondelete="CASCADE", index=True
    )
    action: str = Field(max_length=20, index=True)
    actor_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    reason_code: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    diff_json: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
