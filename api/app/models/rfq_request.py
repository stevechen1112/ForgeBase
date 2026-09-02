import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class RFQProductLink(SQLModel, table=True):
    """M2M: RFQRequest ↔ Product (products_of_interest)"""
    __tablename__ = "rfq_product_links"
    rfq_id: uuid.UUID = Field(
        foreign_key="rfq_requests.id", ondelete="CASCADE", primary_key=True
    )
    product_id: uuid.UUID = Field(
        foreign_key="products.id", ondelete="CASCADE", primary_key=True
    )


class RFQRequest(SQLModel, table=True):
    """
    RFQ (Request For Quotation) submitted via the RFQ form.
    Auto-assigned an rfq_number. Routed to sales users.
    Spec: 12.7.4, 12.7.5, 1b.4.5
    """
    __tablename__ = "rfq_requests"
    __table_args__ = (
        UniqueConstraint("rfq_number", name="uq_rfq_number"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    rfq_number: str = Field(max_length=30, index=True)
    # Format: RFQ-YYYYMMDD-NNN, e.g. RFQ-20260314-001

    # Requester  
    contact_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="contacts.id", ondelete="SET NULL", index=True
    )
    visitor_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="visitors.visitor_id",
        ondelete="SET NULL",
    )

    # Products of interest stored in rfq_product_links; also keep raw JSON
    application_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="applications.id", ondelete="SET NULL"
    )

    # Form data (full JSON snapshot of what was submitted)
    form_data: Optional[str] = Field(default=None)
    # JSON: {full_name, company_name, email, phone, country, job_title,
    #        quantity, specifications, timeline, message, how_did_you_find_us}

    # First-party website context captured when the RFQ was submitted. This is
    # provenance for triage, not CRM or closed-loop revenue attribution.
    source_context_json: Optional[str] = Field(default=None)

    # Durable Chat -> RFQ provenance
    source_chat_session_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="chat_sessions.id",
        ondelete="SET NULL",
        index=True,
    )
    source_draft_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="rfq_drafts.id", ondelete="SET NULL", index=True
    )

    # Website-to-sales handoff state.  ForgeBase stops at accepted/archived;
    # quotation, negotiation, won/lost and revenue belong in a CRM.
    status: str = Field(default="new", max_length=20, index=True)
    # "new" | "assigned" | "accepted" | "archived"

    # Routing & assignment
    assigned_to: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )
    priority: str = Field(default="normal", max_length=10)
    # "normal" | "high" | "urgent"

    source_page: Optional[str] = Field(default=None, max_length=500)

    # Notification flags (1b.4.7)
    assigned_notified_at: Optional[datetime] = Field(default=None)
    reminder_24h_sent_at: Optional[datetime] = Field(default=None)
    escalation_48h_sent_at: Optional[datetime] = Field(default=None)

    # Verifiable handoff timestamps.  Assignment, automatic acknowledgement,
    # human acceptance and a substantive reply are deliberately separate.
    acknowledgement_sent_at: Optional[datetime] = Field(default=None)
    accepted_at: Optional[datetime] = Field(default=None, index=True)
    first_verified_response_at: Optional[datetime] = Field(default=None)
    archived_at: Optional[datetime] = Field(default=None, index=True)

    # Operational triage. Spam and merged records remain auditable and are
    # hidden from the default work queue instead of being deleted.
    is_spam: bool = Field(default=False, index=True)
    spam_reason: Optional[str] = Field(default=None, max_length=500)
    spam_marked_at: Optional[datetime] = Field(default=None)
    spam_marked_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    merged_into_rfq_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="rfq_requests.id",
        index=True,
    )
    merged_at: Optional[datetime] = Field(default=None)

    # Operational smoke-test records are retained for audit but excluded from
    # customer-facing metrics and the default sales queue.
    is_test_data: bool = Field(default=False, index=True)
    test_run_id: Optional[str] = Field(default=None, max_length=100)

    # Timezone-aware acceptance SLA.  It measures whether the assigned owner
    # accepted the RFQ, never whether an offline phone/video response happened.
    buyer_timezone: Optional[str] = Field(default=None, max_length=50)
    acceptance_due_at: Optional[datetime] = Field(default=None, index=True)
    acceptance_sla_breached: bool = Field(default=False)

    # Trade terms (T10: optional form step 2 — strong buyer signals)
    incoterm: Optional[str] = Field(default=None, max_length=10)
    annual_volume: Optional[str] = Field(default=None, max_length=100)
    is_trial_order: Optional[bool] = Field(default=None)
    required_certs_json: Optional[str] = Field(default=None)
    # JSON list of certification names, e.g. ["FDA","CE"]
    target_price: Optional[str] = Field(default=None, max_length=100)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
