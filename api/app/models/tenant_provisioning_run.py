import uuid
from datetime import datetime

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class TenantProvisioningRun(SQLModel, table=True):
    """Durable replay ledger for one atomic tenant-delivery factory request."""

    __tablename__ = "tenant_provisioning_runs"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_tenant_provisioning_runs_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    idempotency_key: str = Field(max_length=128, index=True)
    request_fingerprint: str = Field(max_length=64)
    actor_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    status_code: int = Field(default=201)
    response_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
