import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class Contact(SQLModel, table=True):
    """
    Known contact: created from RFQ or Contact form submission.
    (tenant_id, email) is the dedup key — same email merges into same Contact
    within a tenant; different tenants may hold separate records for the
    same email (multi-tenant isolation, 2026-08-03).
    Visitors link to the contact through ``Visitor.contact_id``.  Keeping the
    relationship on the visitor side allows multiple browser identities to be
    resolved to one known contact without a circular foreign key.
    Spec: 12.7.3, 1b.2.3
    """
    __tablename__ = "contacts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_contacts_tenant_email"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    email: str = Field(max_length=254, index=True)
    full_name: str = Field(max_length=200)
    company_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    country: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=80)

    intent_score_at_creation: int = Field(default=0)

    # HubSpot CRM linkage (1b.5.2)
    hubspot_contact_id: str | None = Field(default=None, max_length=50)

    # Submission source
    source_page: str | None = Field(default=None, max_length=500)
    how_did_you_find_us: str | None = Field(default=None, max_length=30)

    # A manually converted company-related candidate is deliberately not
    # linked to the anonymous visitor.  This opaque provenance reference lets
    # reviewers trace the decision without asserting personal identity.
    source_type: str | None = Field(default=None, max_length=40, index=True)
    source_reference_id: uuid.UUID | None = Field(default=None, index=True)

    notes: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
