import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class RFQEvent(SQLModel, table=True):
    """
    Append-only audit log for RFQ lifecycle events.
    Every status change, assignment, follow-up action is recorded here.
    """
    __tablename__ = "rfq_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    rfq_id: uuid.UUID = Field(
        foreign_key="rfq_requests.id", ondelete="CASCADE", index=True
    )
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id")

    # Who performed the action (None = system/auto)
    actor_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    # Event classification
    event_type: str = Field(max_length=40, index=True)
    # "created" | "status_changed" | "assigned" | "priority_changed"
    # "first_response" | "quote_sent" | "lost_reason_set"
    # "notification_sent" | "ai_analysis_run" | "draft_reply_generated"

    # Human-readable summary, e.g. "Status changed from new to assigned"
    summary: str = Field(max_length=500)

    # Structured detail (optional JSON)
    detail: Optional[str] = Field(default=None)
    # e.g. {"old_status": "new", "new_status": "assigned"}

    created_at: datetime = Field(default_factory=utcnow_naive)
