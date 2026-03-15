"""
Nurture Models — 2.1.4 Email Nurture Engine.

A NurtureSequence is a named email workflow with:
  - trigger_type: "intent_stage" | "segment" | "manual"
  - trigger_value: e.g. "hot" or segment_id
  - Steps: ordered list of emails with delay_days

A NurtureEnrollment tracks a contact's progress through a sequence.
"""
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional

from sqlmodel import SQLModel, Field


class NurtureSequence(SQLModel, table=True):
    """
    Named email nurture workflow.
    Triggered when a visitor/contact meets the trigger condition.
    """
    __tablename__ = "nurture_sequences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None)

    # Trigger configuration
    trigger_type: str = Field(max_length=30)
    # "intent_stage" | "segment" | "download_gate" | "manual"
    trigger_value: Optional[str] = Field(default=None, max_length=200)
    # For intent_stage: "warm"|"hot"|"sales_ready"
    # For segment: segment UUID
    # For download_gate: gate/asset UUID

    # Enrollment settings
    is_active: bool = Field(default=True)
    allow_re_enrollment: bool = Field(default=False)
    # If True, re-enroll even if already completed

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class NurtureStep(SQLModel, table=True):
    """
    Individual email step within a NurtureSequence.
    delay_days: wait N days after previous step (0 = immediate).
    """
    __tablename__ = "nurture_steps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sequence_id: uuid.UUID = Field(foreign_key="nurture_sequences.id", index=True)

    step_order: int = Field(default=0)
    # 0-indexed step position within the sequence
    delay_days: int = Field(default=0)
    # Days to wait after enrollment (step 0) or previous step

    # Email content
    subject: str = Field(max_length=500)
    html_body: Optional[str] = Field(default=None)
    text_body: Optional[str] = Field(default=None)
    from_name: Optional[str] = Field(default=None, max_length=200)
    from_email: Optional[str] = Field(default=None, max_length=200)
    # Falls back to settings.EMAIL_FROM / settings.EMAIL_FROM_NAME

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class NurtureEnrollment(SQLModel, table=True):
    """
    Tracks a contact's enrollment and progress through a NurtureSequence.
    One enrollment per (contact_id, sequence_id) unless allow_re_enrollment=True.
    """
    __tablename__ = "nurture_enrollments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sequence_id: uuid.UUID = Field(foreign_key="nurture_sequences.id", index=True)
    contact_id: uuid.UUID = Field(foreign_key="contacts.id", index=True)

    status: str = Field(default="active", max_length=20)
    # "active" | "completed" | "unsubscribed" | "bounced"

    current_step: int = Field(default=0)
    # Index of the next step to send

    enrolled_at: datetime = Field(default_factory=utcnow_naive)
    last_sent_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    unsubscribed_at: Optional[datetime] = Field(default=None)

    # Trigger context
    trigger_type: Optional[str] = Field(default=None, max_length=30)
    trigger_value: Optional[str] = Field(default=None, max_length=200)
