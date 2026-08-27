import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ChatSession(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    visitor_id: uuid.UUID = Field(foreign_key="visitors.visitor_id", index=True)
    session_id: Optional[uuid.UUID] = Field(default=None, index=True)
    context_page: Optional[str] = Field(default=None, max_length=500)
    context_entity_type: Optional[str] = Field(default=None, max_length=30)
    context_entity_id: Optional[uuid.UUID] = Field(default=None, index=True)
    locale: str = Field(default="en", max_length=10)
    started_at: datetime = Field(default_factory=utcnow_naive)
    ended_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="active", max_length=20)
    message_count: int = Field(default=0)
    quality_rating: Optional[int] = Field(default=None)  # 1-5 admin quality rating
    admin_notes: Optional[str] = Field(default=None)  # admin review notes
    qualification_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    chat_session_id: uuid.UUID = Field(
        foreign_key="chat_sessions.id",
        ondelete="CASCADE",
        index=True,
    )
    role: str = Field(max_length=10)
    content: str
    sources: Optional[str] = Field(default=None)
    grounding_status: Optional[str] = Field(default=None, max_length=20)
    claim_warnings: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow_naive)
