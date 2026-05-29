import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from app.core.datetime import utcnow_naive


class RFQProductLink(SQLModel, table=True):
    """M2M: RFQRequest ↔ Product (products_of_interest)"""
    __tablename__ = "rfq_product_links"
    rfq_id: uuid.UUID = Field(foreign_key="rfq_requests.id", primary_key=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", primary_key=True)


class RFQRequest(SQLModel, table=True):
    """
    RFQ (Request For Quotation) submitted via the RFQ form.
    Auto-assigned an rfq_number. Routed to sales users.
    Spec: 12.7.4, 12.7.5, 1b.4.5
    """
    __tablename__ = "rfq_requests"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    rfq_number: str = Field(max_length=30, unique=True, index=True)
    # Format: RFQ-YYYYMMDD-NNN, e.g. RFQ-20260314-001

    # Requester  
    contact_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="contacts.id", index=True
    )
    visitor_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="visitors.visitor_id", index=True
    )

    # Products of interest stored in rfq_product_links; also keep raw JSON
    application_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="applications.id"
    )

    # Form data (full JSON snapshot of what was submitted)
    form_data: Optional[str] = Field(default=None)
    # JSON: {full_name, company_name, email, phone, country, job_title,
    #        quantity, specifications, timeline, message, how_did_you_find_us}

    # Intent at time of submission
    intent_score_at_submit: int = Field(default=0)

    # Status machine (spec 12.7.4)
    status: str = Field(default="new", max_length=20, index=True)
    # "new" | "assigned" | "in_progress" | "quoted" | "won" | "lost" | "expired"

    # Routing & assignment
    assigned_to: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    priority: str = Field(default="normal", max_length=10)
    # "normal" | "high" | "urgent"

    source_page: Optional[str] = Field(default=None, max_length=500)

    # CRM  
    hubspot_deal_id: Optional[str] = Field(default=None, max_length=50)

    # AgentOS integration (Condition 1: auto-trigger)
    agent_run_id: Optional[str] = Field(default=None, max_length=100, index=True)
    # Stores the AgentOS run_id returned when RFQ is auto-triggered

    # AgentOS writeback (Condition 4: writeback)
    agent_analysis_summary: Optional[str] = Field(default=None, max_length=2000)
    # Summary from AgentOS analyze-rfq evidence (forgebase_analyze_rfq)
    agent_draft_body: Optional[str] = Field(default=None)
    # Approved reply draft body from AgentOS send-reply evidence (forgebase_send_reply)

    # Notification flags (1b.4.7)
    assigned_notified_at: Optional[datetime] = Field(default=None)
    reminder_24h_sent_at: Optional[datetime] = Field(default=None)
    escalation_48h_sent_at: Optional[datetime] = Field(default=None)

    # Sales follow-up timestamps
    first_response_at: Optional[datetime] = Field(default=None)
    quote_sent_at: Optional[datetime] = Field(default=None)
    lost_reason: Optional[str] = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    closed_at: Optional[datetime] = Field(default=None)
