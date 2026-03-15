import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class Capability(SQLModel, table=True):
    """Factory capability / manufacturing process cards shown on About / Home."""
    __tablename__ = "capabilities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    capability_name: str = Field(max_length=100, index=True)
    slug: str = Field(max_length=100, unique=True, index=True)
    icon_url: Optional[str] = Field(default=None, max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=500)
    short_description: str = Field(max_length=200)
    detail: Optional[str] = Field(default=None)   # richtext
    metrics: Optional[str] = Field(default=None)
    # JSON: [{"label": "Tonnage", "value": "80T-2000T"}]
    category_tag: Optional[str] = Field(default=None, max_length=60)
    sort_order: int = Field(default=0)
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="draft", max_length=20)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    published_at: Optional[datetime] = Field(default=None)
