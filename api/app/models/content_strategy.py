import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ContentStrategy(SQLModel, table=True):
    """
    Content planning matrix entry.
    Tracks: page_type × entity → planning status.
    Used for the editorial calendar / content gap analysis view.
    """
    __tablename__ = "content_strategies"
    __table_args__ = (
        Index("ix_content_strategies_entity", "entity_type", "entity_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # What kind of page this entry plans for
    page_type: str = Field(max_length=40, index=True)
    # "product" | "application" | "category" | "comparison" | "faq" | "about" | "contact"

    # Optional link to a specific entity (Product, Application, etc.)
    entity_type: Optional[str] = Field(default=None, max_length=40)
    # "product" | "application" | "category" | "comparison" | None (page-level)
    entity_id: Optional[uuid.UUID] = Field(default=None)

    # Planning status
    status: str = Field(default="unplanned", max_length=30, index=True)
    # "unplanned" | "planned" | "in_progress" | "published"

    locale: str = Field(default="en", max_length=5)
    notes: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
