import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class EmailDeliveryEvent(SQLModel, table=True):
    """Privacy-minimised, replay-safe ESP delivery event ledger."""

    __tablename__ = "email_delivery_events"
    __table_args__ = (
        UniqueConstraint(
            "provider_event_id", name="uq_email_delivery_events_provider_event_id"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    outreach_message_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="outreach_messages.id",
        ondelete="SET NULL",
        index=True,
    )
    provider: str = Field(default="resend", max_length=20, index=True)
    provider_event_id: str = Field(max_length=120, index=True)
    provider_message_id: Optional[str] = Field(default=None, max_length=120, index=True)
    event_type: str = Field(max_length=50, index=True)
    recipient_hash: Optional[str] = Field(default=None, max_length=64, index=True)
    recipient_masked: Optional[str] = Field(default=None, max_length=254)
    reason_code: Optional[str] = Field(default=None, max_length=100)
    event_data_json: str = Field(default="{}", sa_column=Column(Text, nullable=False))
    is_unknown_message: bool = Field(default=False, index=True)
    occurred_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)


class EmailSuppression(SQLModel, table=True):
    """Global recipient suppression derived from bounce/complaint events."""

    __tablename__ = "email_suppressions"
    __table_args__ = (
        UniqueConstraint(
            "scope_key", "email_hash", name="uq_email_suppression_scope_hash"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    scope_key: str = Field(default="global", max_length=80, index=True)
    email_hash: str = Field(max_length=64, index=True)
    email_masked: str = Field(max_length=254)
    reason: str = Field(max_length=50, index=True)
    provider: str = Field(default="resend", max_length=20)
    source_event_id: Optional[str] = Field(default=None, max_length=120)
    active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
