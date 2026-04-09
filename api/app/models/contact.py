import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from app.core.datetime import utcnow_naive


class Contact(SQLModel, table=True):
    """
    Known contact: created from RFQ or Contact form submission.
    email is the dedup key — same email merges into same Contact.
    Linked back to original Visitor for full behavioral timeline.
    Spec: 12.7.3, 1b.2.3
    """
    __tablename__ = "contacts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    email: str = Field(max_length=100, unique=True, index=True)
    full_name: str = Field(max_length=100)
    company_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    country: Optional[str] = Field(default=None, max_length=50)
    job_title: Optional[str] = Field(default=None, max_length=80)

    # First-touch visitor linkage (1b.2.4: visitor → contact merge)
    visitor_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="visitors.visitor_id", index=True
    )
    intent_score_at_creation: int = Field(default=0)

    # HubSpot CRM linkage (1b.5.2)
    hubspot_contact_id: Optional[str] = Field(default=None, max_length=50)

    # Submission source
    source_page: Optional[str] = Field(default=None, max_length=500)
    how_did_you_find_us: Optional[str] = Field(default=None, max_length=30)

    notes: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
