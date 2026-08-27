import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ConsentRecord(SQLModel, table=True):
    """Append-only privacy decision audit without retaining the raw visitor id."""

    __tablename__ = "consent_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID | None = Field(default=None, foreign_key="tenants.id", index=True)
    visitor_hash: str = Field(max_length=64, index=True)
    status: str = Field(max_length=20, index=True)
    policy_version: str = Field(max_length=40)
    source: str = Field(default="web", max_length=30)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
