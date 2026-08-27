"""Silent locks: fields on a locale variant that must not be overwritten by auto-sync."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ContentFieldLock(SQLModel, table=True):
    __tablename__ = "content_field_locks"
    __table_args__ = (
        UniqueConstraint(
            "entity_type",
            "entity_id",
            "field_name",
            name="uq_content_field_locks_entity_field",
        ),
        Index("ix_content_field_locks_entity", "entity_type", "entity_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id")
    entity_type: str = Field(max_length=40)
    entity_id: uuid.UUID
    field_name: str = Field(max_length=80)
    created_at: datetime = Field(default_factory=utcnow_naive)
