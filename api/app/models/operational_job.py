import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class OperationalJob(SQLModel, table=True):
    """Durable outbox for RFQ and visitor follow-up side effects."""

    __tablename__ = "operational_jobs"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="operational_jobs_idempotency_key_key"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tenants.id", ondelete="CASCADE", index=True
    )
    job_type: str = Field(max_length=50, index=True)
    payload_json: str
    status: str = Field(default="pending", max_length=20, index=True)
    attempts: int = Field(default=0)
    max_attempts: int = Field(default=5)
    available_at: datetime = Field(default_factory=utcnow_naive, index=True)
    locked_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    last_error: Optional[str] = Field(default=None, max_length=2000)
    idempotency_key: str = Field(max_length=200, index=True)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
