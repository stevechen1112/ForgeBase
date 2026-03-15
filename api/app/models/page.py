import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class Page(SQLModel, table=True):
    """Static / landing pages: Home, About, Contact, custom landing pages, etc."""
    __tablename__ = "pages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    page_type: str = Field(max_length=40, index=True)
    # Values: "home" | "about" | "contact" | "landing" | "blog_post"
    slug: str = Field(max_length=120, unique=True, index=True)
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
    # Source entity and brief links (spec 12.2.9)
    entity_type: Optional[str] = Field(default=None, max_length=40)
    # "product" | "application" | "certification" | "capability" | None
    entity_id: Optional[uuid.UUID] = Field(default=None)
    brief_id: Optional[uuid.UUID] = Field(default=None, foreign_key="page_briefs.id")
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    published_at: Optional[datetime] = Field(default=None)
