import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class NotificationPreference(SQLModel, table=True):
    """
    Per-user notification channel preferences and event toggles.
    Each row = one user + one channel (telegram / line / email / in_app).
    """
    __tablename__ = "notification_preferences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", ondelete="CASCADE", index=True
    )
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id", ondelete="CASCADE", index=True
    )

    # Channel: 'telegram' | 'line' | 'email' | 'in_app'
    channel: str = Field(max_length=20)
    # JSON config: {"chat_id": "123456"} for telegram, {"line_user_id": "U..."} for line
    channel_config: str = Field(default="{}")

    enabled: bool = Field(default=True)

    # Event toggle switches
    notify_new_rfq: bool = Field(default=True)
    notify_hot_visitor: bool = Field(default=True)
    notify_daily_summary: bool = Field(default=True)
    notify_churn_risk: bool = Field(default=False)
    notify_chat_handoff: bool = Field(default=True)
    notify_content_suggestion: bool = Field(default=False)

    # Quiet hours (null = no quiet hours)
    quiet_hours_start: Optional[str] = Field(default=None, max_length=5)  # "HH:MM"
    quiet_hours_end: Optional[str] = Field(default=None, max_length=5)    # "HH:MM"

    # Telegram binding: one-time verification code (expires after use)
    binding_code: Optional[str] = Field(default=None, max_length=10, index=True)
    binding_code_expires_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
