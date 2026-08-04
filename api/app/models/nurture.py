"""
Nurture Models — Email Nurture Engine.

A NurtureSequence is a named email workflow with:
  - trigger_type: "intent_stage" | "segment" | "manual"
  - trigger_value: e.g. "warm" / "hot" or segment id
  - Steps: ordered list of emails with delay_days

A NurtureEnrollment tracks a contact's progress through a sequence.
"""
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional

from sqlmodel import SQLModel, Field


class NurtureSequence(SQLModel, table=True):
    """Named email nurture workflow, enrolled when the trigger condition is met."""
    __tablename__ = "nurture_sequences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None)

    trigger_type: str = Field(max_length=30)
    # "intent_stage" | "segment" | "manual"
    trigger_value: Optional[str] = Field(default=None, max_length=200)
    # intent_stage: "warm" | "hot" | "sales_ready"; segment: segment UUID

    is_active: bool = Field(default=True)
    allow_re_enrollment: bool = Field(default=False)

    # Approval gate: sequence must be approved before any email is sent.
    is_approved: bool = Field(default=False, sa_column_kwargs={"server_default": "false"})
    approved_at: Optional[datetime] = Field(default=None)
    approved_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class NurtureStep(SQLModel, table=True):
    """One email in a sequence; delay_days waits after enrollment or previous step."""
    __tablename__ = "nurture_steps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    sequence_id: uuid.UUID = Field(foreign_key="nurture_sequences.id", index=True)

    step_order: int = Field(default=0)
    delay_days: int = Field(default=0)

    subject: str = Field(max_length=500)
    html_body: Optional[str] = Field(default=None)
    text_body: Optional[str] = Field(default=None)
    from_name: Optional[str] = Field(default=None, max_length=200)
    from_email: Optional[str] = Field(default=None, max_length=200)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class NurtureEnrollment(SQLModel, table=True):
    """A contact's enrollment and progress through a NurtureSequence."""
    __tablename__ = "nurture_enrollments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    sequence_id: uuid.UUID = Field(foreign_key="nurture_sequences.id", index=True)
    contact_id: uuid.UUID = Field(foreign_key="contacts.id", index=True)

    status: str = Field(default="active", max_length=20)
    # "active" | "completed" | "unsubscribed" | "bounced"

    current_step: int = Field(default=0)

    enrolled_at: datetime = Field(default_factory=utcnow_naive)
    last_sent_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    unsubscribed_at: Optional[datetime] = Field(default=None)

    trigger_type: Optional[str] = Field(default=None, max_length=30)
    trigger_value: Optional[str] = Field(default=None, max_length=200)


class NurtureOutbox(SQLModel, table=True):
    """One queued nurture email awaiting manual approval before send."""
    __tablename__ = "nurture_outbox"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    enrollment_id: uuid.UUID = Field(foreign_key="nurture_enrollments.id", index=True)
    sequence_id: uuid.UUID = Field(foreign_key="nurture_sequences.id", index=True)
    step_id: uuid.UUID = Field(foreign_key="nurture_steps.id", index=True)
    contact_id: uuid.UUID = Field(foreign_key="contacts.id", index=True)

    status: str = Field(default="pending", max_length=20)
    # "pending" | "sent" | "skipped" | "failed"

    subject: str = Field(max_length=500)
    due_at: datetime = Field(default_factory=utcnow_naive)
    created_at: datetime = Field(default_factory=utcnow_naive)
    reviewed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    reviewed_at: Optional[datetime] = Field(default=None)
    sent_at: Optional[datetime] = Field(default=None)
    error: Optional[str] = Field(default=None)

