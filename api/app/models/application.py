import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.datetime import utcnow_naive
from app.models.associations import (
    ApplicationFAQLink,
    ApplicationRelatedLink,
    ProductApplicationLink,
)

if TYPE_CHECKING:
    from app.models.faq_item import FAQItem
    from app.models.product import Product


class Application(SQLModel, table=True):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("slug", "locale", "tenant_id", name="uq_applications_slug_locale_tenant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    application_name: str = Field(max_length=100, index=True)
    slug: str = Field(max_length=100, index=True)
    industry: str = Field(max_length=60)      # e.g. "Automotive", "Electronics"
    description: Optional[str] = Field(default=None)   # richtext
    challenge: Optional[str] = Field(default=None)     # richtext — pain points solved
    solution: Optional[str] = Field(default=None)      # richtext — how product solves it
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    og_image_url: Optional[str] = Field(default=None, max_length=500)  # OG-specific image (1200×630)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: str = Field(default="draft", max_length=20)
    locale: str = Field(default="en", max_length=5)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    published_at: Optional[datetime] = Field(default=None)

    # Relationships
    products: List["Product"] = Relationship(
        back_populates="applications", link_model=ProductApplicationLink
    )
    faqs: List["FAQItem"] = Relationship(
        back_populates="applications", link_model=ApplicationFAQLink
    )
    related_applications: List["Application"] = Relationship(
        back_populates="related_applications",
        link_model=ApplicationRelatedLink,
        sa_relationship_kwargs={
            "primaryjoin": "Application.id == ApplicationRelatedLink.application_id",
            "secondaryjoin": "Application.id == ApplicationRelatedLink.related_application_id",
            "lazy": "select",
        },
    )
