import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class PrivacyOperation(SQLModel, table=True):
    """PII-minimised, replay-safe ledger for privileged privacy operations."""

    __tablename__ = "privacy_operations"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_privacy_operations_key"),
        CheckConstraint(
            "operation_type IN ('retention_run', 'visitor_export', 'visitor_erasure')",
            name="ck_privacy_operation_type",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')", name="ck_privacy_operation_status"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    idempotency_key: str = Field(max_length=128, index=True)
    request_fingerprint: str = Field(max_length=64)
    operation_type: str = Field(max_length=30, index=True)
    tenant_id: uuid.UUID | None = Field(
        default=None, foreign_key="tenants.id", ondelete="SET NULL", index=True
    )
    actor_user_id: uuid.UUID | None = Field(
        default=None, foreign_key="users.id", ondelete="SET NULL", index=True
    )
    subject_hash: str | None = Field(default=None, max_length=64, index=True)
    reason: str | None = Field(default=None, max_length=500)
    status: str = Field(default="completed", max_length=20, index=True)
    result_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
    completed_at: datetime = Field(default_factory=utcnow_naive)
