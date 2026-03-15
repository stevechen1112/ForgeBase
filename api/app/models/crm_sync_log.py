"""
2.4.1/2.4.2 CRM 整合 — Sync Log model
Tracks individual push/pull sync operations with external CRMs.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class CrmSyncLog(SQLModel, table=True):
    __tablename__ = "crm_sync_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    crm: str = Field(index=True)                   # "salesforce" | "hubspot"
    direction: str = Field(default="push")         # "push" | "pull"
    entity_type: str = Field(index=True)           # "contact" | "opportunity" | "rfq"
    local_id: Optional[str] = Field(default=None)  # our FK (contact.id / rfq.id)
    remote_id: Optional[str] = Field(default=None) # Salesforce ID / HubSpot ID
    status: str = Field(default="success")         # "success" | "error" | "skipped"
    error_message: Optional[str] = None
    payload_summary: Optional[str] = None          # brief description of what was synced
    synced_at: datetime = Field(default_factory=datetime.utcnow, index=True)
