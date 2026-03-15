"""
2.1.6 LinkedIn Audience 同步 — LinkedIn Audience model
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class LinkedInAudience(SQLModel, table=True):
    """Tracks LinkedIn DMP Segment sync jobs."""

    __tablename__ = "linkedin_audiences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None

    # LinkedIn identifiers
    linkedin_segment_id: Optional[str] = Field(default=None, index=True)
    audience_type: str = Field(default="EMAIL")  # "EMAIL" | "COMPANY"

    # Source criteria — which entities to sync
    source_type: str = Field(default="segment")  # "segment" | "contacts_all" | "custom"
    source_segment_id: Optional[str] = None  # FK soft-ref to audience_segments.id

    # Status
    status: str = Field(default="pending")  # pending | syncing | synced | error
    last_sync_at: Optional[datetime] = None
    last_record_count: int = Field(default=0)
    error_message: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
