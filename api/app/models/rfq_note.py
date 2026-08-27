import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class RFQNote(SQLModel, table=True):
    """Tenant-scoped internal note attached to an RFQ sales case."""

    __tablename__ = "rfq_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    rfq_id: uuid.UUID = Field(foreign_key="rfq_requests.id", index=True)
    author_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    body: str = Field(max_length=4000)
    created_at: datetime = Field(default_factory=utcnow_naive, index=True)
