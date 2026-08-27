import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class RFQDraft(SQLModel, table=True):
    """Short-lived, server-side handoff from an owned chat session to RFQ."""

    __tablename__ = "rfq_drafts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    visitor_id: uuid.UUID = Field(
        foreign_key="visitors.visitor_id", ondelete="CASCADE", index=True
    )
    chat_session_id: uuid.UUID = Field(
        foreign_key="chat_sessions.id", ondelete="CASCADE", index=True
    )
    payload_json: str
    expires_at: datetime = Field(index=True)
    consumed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
