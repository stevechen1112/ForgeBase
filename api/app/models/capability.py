import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint


class Capability(SQLModel, table=True):
    """Factory capability / manufacturing process cards shown on About / Home."""
    __tablename__ = "capabilities"
    __table_args__ = (
        UniqueConstraint("slug", "locale", "tenant_id", name="uq_capabilities_slug_locale_tenant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    capability_name: str = Field(max_length=100, index=True)
    slug: str = Field(max_length=100, index=True)
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
