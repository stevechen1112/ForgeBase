import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class ContentStrategy(SQLModel, table=True):
    """
    Content planning matrix entry.
    Tracks: page_type × entity → planning status.
    Used for the editorial calendar / content gap analysis view.
    """
    __tablename__ = "content_strategies"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # What kind of page this entry plans for
    page_type: str = Field(max_length=40, index=True)
    # "product" | "application" | "category" | "comparison" | "faq" | "about" | "contact"

    # Optional link to a specific entity (Product, Application, etc.)
    entity_type: Optional[str] = Field(default=None, max_length=40)
    # "product" | "application" | "category" | "comparison" | None (page-level)
    entity_id: Optional[uuid.UUID] = Field(default=None, index=True)

    # Optional link to the brief assigned to this entry
    brief_id: Optional[uuid.UUID] = Field(default=None, foreign_key="page_briefs.id")

    # Planning status
    status: str = Field(default="unplanned", max_length=30, index=True)
    # "unplanned" | "brief_created" | "ai_generated" | "in_review" | "published"

    locale: str = Field(default="en", max_length=5)
    notes: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
