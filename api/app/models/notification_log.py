import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class NotificationLog(SQLModel, table=True):
    """
    Audit log of every notification sent by the copilot system.
    Used for deduplication (prevent repeated alerts) and history display.
    """
    __tablename__ = "notification_log"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tenants.id", ondelete="SET NULL", index=True
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )

    channel: str = Field(max_length=20)
    # Event types: 'new_rfq' | 'hot_visitor' | 'daily_summary' | 'churn_risk' | 'chat_handoff'
    event_type: str = Field(max_length=50, index=True)
    # Optional FK to the triggering entity (rfq_id, visitor_id, etc.)
    event_ref_id: Optional[uuid.UUID] = Field(default=None, index=True)

    message_preview: Optional[str] = Field(default=None, max_length=500)
    # 'sent' | 'delivered' | 'failed' | 'skipped_quiet_hours' | 'skipped_rate_limit'
    status: str = Field(default="sent", max_length=30)
    error_detail: Optional[str] = Field(default=None)

    sent_at: datetime = Field(default_factory=utcnow_naive)
