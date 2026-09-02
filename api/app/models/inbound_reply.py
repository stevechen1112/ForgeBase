"""Inbound email receipts and tenant-scoped human sales handoffs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class InboundReplyPolicy(SQLModel, table=True):
    __tablename__ = "inbound_reply_policies"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('off', 'review_only')", name="ck_inbound_reply_policy_mode"
        ),
        CheckConstraint(
            "handoff_sla_hours >= 1 AND handoff_sla_hours <= 168",
            name="ck_inbound_reply_handoff_sla",
        ),
        CheckConstraint(
            "content_retention_days >= 1 AND content_retention_days <= 365",
            name="ck_inbound_reply_retention",
        ),
    )

    tenant_id: uuid.UUID = Field(
        primary_key=True, foreign_key="tenants.id", ondelete="CASCADE"
    )
    mode: str = Field(default="off", max_length=20, index=True)
    handoff_sla_hours: int = Field(default=4, ge=1, le=168)
    content_retention_days: int = Field(default=90, ge=1, le=365)
    updated_by: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class InboundReply(SQLModel, table=True):
    """Encrypted, privacy-minimised inbound content and classification result."""

    __tablename__ = "inbound_replies"
    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_event_id", name="uq_inbound_reply_provider_event"
        ),
        UniqueConstraint(
            "provider", "provider_email_id", name="uq_inbound_reply_provider_email"
        ),
        CheckConstraint(
            "status IN ('fetch_pending', 'processing', 'classified', 'needs_review', "
            "'handed_off', 'ignored', 'failed')",
            name="ck_inbound_reply_status",
        ),
        CheckConstraint(
            "classification IN ('unknown', 'positive', 'question', 'rfq', 'not_now', "
            "'wrong_person', 'unsubscribe', 'negative', 'auto_reply', 'bounce')",
            name="ck_inbound_reply_classification",
        ),
        CheckConstraint(
            "classification_confidence >= 0 AND classification_confidence <= 1",
            name="ck_inbound_reply_confidence",
        ),
        CheckConstraint(
            "body_char_count >= 0 AND attachment_count >= 0 AND attachment_total_bytes >= 0",
            name="ck_inbound_reply_nonnegative_counts",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    outreach_message_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="outreach_messages.id",
        ondelete="SET NULL",
        index=True,
    )
    parent_reply_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="inbound_replies.id",
        ondelete="SET NULL",
        index=True,
    )
    provider: str = Field(default="resend", max_length=20, index=True)
    provider_event_id: str = Field(max_length=120, index=True)
    provider_email_id: str = Field(max_length=120, index=True)
    rfc_message_id: str | None = Field(default=None, max_length=500, index=True)
    in_reply_to: str | None = Field(default=None, max_length=500, index=True)
    references: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )

    sender_email_ciphertext: str = Field(
        sa_column=Column(Text, nullable=False), repr=False
    )
    sender_email_hash: str = Field(max_length=64, index=True, repr=False)
    sender_email_masked: str = Field(max_length=254)
    route_address_hash: str | None = Field(default=None, max_length=64, index=True)
    subject_ciphertext: str = Field(sa_column=Column(Text, nullable=False), repr=False)
    body_text_ciphertext: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True), repr=False
    )
    body_sha256: str | None = Field(default=None, max_length=64, repr=False)
    body_char_count: int = Field(default=0, ge=0)

    attachment_metadata: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    attachment_count: int = Field(default=0, ge=0)
    attachment_total_bytes: int = Field(
        default=0, sa_column=Column(BigInteger, nullable=False, default=0)
    )
    attachments_quarantined: bool = Field(default=False, index=True)

    classification: str = Field(default="unknown", max_length=30, index=True)
    classification_confidence: float = Field(default=0.0, ge=0, le=1)
    classification_reasons: list[str] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False, default=list)
    )
    status: str = Field(default="fetch_pending", max_length=30, index=True)
    stops_automation: bool = Field(default=False, index=True)
    needs_human_review: bool = Field(default=True, index=True)
    processing_error: str | None = Field(default=None, max_length=2000)
    raw_payload_sha256: str = Field(max_length=64, repr=False)

    received_at: datetime = Field(index=True)
    fetched_at: datetime | None = Field(default=None)
    classified_at: datetime | None = Field(default=None)
    expires_at: datetime = Field(index=True)
    content_redacted_at: datetime | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive, index=True)


class SalesHandoff(SQLModel, table=True):
    """Assignable human-sales task created from a valuable inbound reply."""

    __tablename__ = "sales_handoffs"
    __table_args__ = (
        UniqueConstraint("inbound_reply_id", name="uq_sales_handoff_inbound_reply"),
        CheckConstraint(
            "status IN ('new', 'accepted', 'converted_to_rfq', 'closed')",
            name="ck_sales_handoff_status",
        ),
        CheckConstraint(
            "priority IN ('normal', 'high', 'urgent')",
            name="ck_sales_handoff_priority",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    inbound_reply_id: uuid.UUID = Field(
        foreign_key="inbound_replies.id", ondelete="CASCADE", index=True
    )
    outreach_message_id: uuid.UUID = Field(
        foreign_key="outreach_messages.id", ondelete="CASCADE", index=True
    )
    rfq_id: uuid.UUID | None = Field(
        default=None, foreign_key="rfq_requests.id", ondelete="SET NULL", index=True
    )
    owner_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )
    status: str = Field(default="new", max_length=30, index=True)
    priority: str = Field(default="normal", max_length=10, index=True)
    classification: str = Field(max_length=30, index=True)
    summary: str = Field(max_length=1000)
    sla_due_at: datetime = Field(index=True)
    sla_breached: bool = Field(default=False, index=True)
    accepted_at: datetime | None = Field(default=None)
    closed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive, index=True)


class SalesHandoffEvent(SQLModel, table=True):
    """Append-only audit log for handoff decisions and RFQ conversion."""

    __tablename__ = "sales_handoff_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'accepted', 'assigned', 'linked_rfq', "
            "'created_rfq', 'marked_wrong_person', 'unsubscribed', 'closed')",
            name="ck_sales_handoff_event_action",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    sales_handoff_id: uuid.UUID = Field(
        foreign_key="sales_handoffs.id", ondelete="CASCADE", index=True
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )
    action: str = Field(max_length=30, index=True)
    note: str | None = Field(default=None, max_length=2000)
    detail: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict)
    )
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
