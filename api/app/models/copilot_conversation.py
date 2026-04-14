import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

from app.core.datetime import utcnow_naive


class CopilotConversation(SQLModel, table=True):
    """
    AI Copilot dialogue history for Telegram / LINE / in-app channels.
    Stores multi-turn context per user per channel.
    """
    __tablename__ = "copilot_conversations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)

    # Channel identification
    channel: str = Field(max_length=20)           # 'telegram' | 'line' | 'in_app'
    channel_user_id: str = Field(max_length=200, index=True)  # telegram chat_id / line user_id

    role: str = Field(max_length=10)              # 'user' | 'assistant'
    content: str
    # JSON array of {type, function: {name, arguments}} if assistant called tools
    tool_calls: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow_naive)
