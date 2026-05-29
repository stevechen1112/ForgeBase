import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class PageBrief(SQLModel, table=True):
    """Content brief for AI-assisted page generation — stores intent, audience, keywords."""
    __tablename__ = "page_briefs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    target_page_type: str = Field(max_length=40)   # maps to Page.page_type
    target_slug: Optional[str] = Field(default=None, max_length=120)
    title_draft: Optional[str] = Field(default=None, max_length=120)
    audience_persona: Optional[str] = Field(default=None, max_length=200)
    buyer_stage: Optional[str] = Field(default=None, max_length=40)
    # "awareness" | "consideration" | "decision"
    primary_keyword: Optional[str] = Field(default=None, max_length=100)
    secondary_keywords: Optional[str] = Field(default=None)    # JSON array
    tone: Optional[str] = Field(default=None, max_length=40)
    # "technical" | "friendly" | "authoritative"
    word_count_target: Optional[int] = Field(default=None)
    main_cta_key: Optional[str] = Field(default=None, max_length=60)
    notes: Optional[str] = Field(default=None)    # free-form text
    # Entity context for AI generation (1a.3.6)
    related_entity_type: Optional[str] = Field(default=None, max_length=40)
    # "product" | "application" | "certification" | "capability" | None
    related_entity_id: Optional[uuid.UUID] = Field(default=None)
    brief_status: str = Field(default="draft", max_length=30)
    # "draft" | "approved" | "in_progress" | "completed" | "published" | "revision"
    ai_status: str = Field(default="pending", max_length=20)
    # "pending" | "processing" | "done" | "error"
    locale: str = Field(default="en", max_length=5)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    created_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    # AgentOS integration fields
    agent_run_id: Optional[str] = Field(default=None, max_length=100, index=True)
    agent_approved_content_json: Optional[str] = Field(default=None)
