import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class Page(SQLModel, table=True):
    """Static / landing pages: Home, About, Contact, custom landing pages, etc."""
    __tablename__ = "pages"
    __table_args__ = (
        UniqueConstraint("slug", "locale", "tenant_id", name="uq_pages_slug_locale_tenant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    page_type: str = Field(max_length=40, index=True)
    # Values: "home" | "about" | "contact" | "landing" | "blog_post"
    slug: str = Field(max_length=120, index=True)
    title: str = Field(max_length=120)
    subtitle: Optional[str] = Field(default=None, max_length=240)
    body: Optional[str] = Field(default=None)     # richtext / blocks JSON
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    structured_data: Optional[str] = Field(default=None)    # JSON-LD string
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="draft", max_length=20)
    noindex: bool = Field(default=False)   # True = add noindex meta tag; auto-set on unpublish
    # Optional source entity link for structured content relationships.
    entity_type: Optional[str] = Field(default=None, max_length=40)
    # "product" | "application" | "certification" | "capability" | None
    entity_id: Optional[uuid.UUID] = Field(default=None)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    published_at: Optional[datetime] = Field(default=None)
