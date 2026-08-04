import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class AIGenerationLog(SQLModel, table=True):
    """
    Tracks every AI generation call for auditability (Epic 1a.4.7).
    """
    __tablename__ = "ai_generation_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)

    brief_id: uuid.UUID = Field(foreign_key="page_briefs.id", index=True)
    triggered_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    page_type: str = Field(max_length=40)
    entity_id: Optional[uuid.UUID] = Field(default=None)

    model_name: str = Field(max_length=80)        # e.g. "gpt-5.6-luna"
    input_summary: Optional[str] = Field(default=None)   # JSON summary of inputs
    output_json: Optional[dict] = Field(default=None, sa_column=Column(JSONB, nullable=True))

    status: str = Field(default="done", max_length=20)
    # "pending" | "processing" | "done" | "error"
    error_message: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow_naive)
