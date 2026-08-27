import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class AdoptionApplication(SQLModel, table=True):
    """A controlled request for a ForgeBase managed-delivery assessment.

    This is intentionally separate from tenant registration and RFQs. A row
    does not create an account, start a trial, or represent an accepted lead.
    """

    __tablename__ = "adoption_applications"
    __table_args__ = (
        UniqueConstraint(
            "application_number", name="uq_adoption_applications_number"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    application_number: str = Field(max_length=40, index=True)
    company_name: str = Field(max_length=200, index=True)
    website_url: str | None = Field(default=None, max_length=500)
    contact_name: str = Field(max_length=100)
    work_email: str = Field(max_length=254, index=True)
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=100)
    industry: str = Field(max_length=120, index=True)
    target_markets: str | None = Field(default=None, max_length=500)
    current_situation: str = Field(max_length=40)
    requested_scope: str = Field(max_length=4000)
    preferred_language: str = Field(default="zh-TW", max_length=10)
    consent: bool = Field(default=False)
    consent_policy_version: str = Field(max_length=30)
    status: str = Field(default="new", max_length=30, index=True)
    internal_note: str | None = Field(default=None, max_length=4000)
    source_page: str | None = Field(default=None, max_length=500)
    source_ip_hash: str | None = Field(default=None, max_length=64)
    is_test_data: bool = Field(default=False, index=True)
    test_run_id: str | None = Field(default=None, max_length=100)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    reviewed_at: datetime | None = Field(default=None)
