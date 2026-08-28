import uuid
from datetime import datetime

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class PlatformAuditLog(SQLModel, table=True):
    """Immutable record of high-impact platform-operator actions."""

    __tablename__ = "platform_audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    actor_user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    # Immutable snapshot keeps the audit legible after an ephemeral operator
    # account is securely removed.
    actor_email: str | None = Field(
        default=None,
        sa_column=Column(String(255), nullable=True),
    )
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    action: str = Field(max_length=80, index=True)
    target_type: str = Field(max_length=50)
    target_id: str | None = Field(default=None, max_length=100)
    changes_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
