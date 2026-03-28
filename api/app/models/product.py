import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from app.core.datetime import utcnow_naive
from app.models.associations import (
    ProductApplicationLink,
    ProductCertificationLink,
    ProductFAQLink,
    ProductComparisonLink,
    AlternativePartLink,
)

if TYPE_CHECKING:
    from app.models.product_category import ProductCategory
    from app.models.application import Application
    from app.models.certification import Certification
    from app.models.faq_item import FAQItem
    from app.models.comparison_topic import ComparisonTopic
    from app.models.content_asset import ContentAsset


class Product(SQLModel, table=True):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("slug", "locale", name="uq_products_slug_locale"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_name: str = Field(max_length=100, index=True)
    slug: str = Field(max_length=100, index=True)
    model_number: str = Field(max_length=50, unique=True)
    short_description: str = Field(max_length=200)
    full_description: Optional[str] = Field(default=None)  # richtext
    specifications: Optional[str] = Field(default=None)    # JSON string: [{name, value, unit}]
    category_id: uuid.UUID = Field(foreign_key="product_categories.id")
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    og_image_url: Optional[str] = Field(default=None, max_length=500)  # OG-specific image (1200×630)
    image_alt: Optional[str] = Field(default=None, max_length=200)    # alt text for main product image
    status: str = Field(default="draft")   # draft / published / archived
    locale: str = Field(default="en", max_length=5)
    is_featured: bool = Field(default=False, index=True)
    display_priority: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
    published_at: Optional[datetime] = Field(default=None)

    # Relationships
    category: Optional["ProductCategory"] = Relationship(back_populates="products")
    applications: List["Application"] = Relationship(
        back_populates="products", link_model=ProductApplicationLink
    )
    certifications: List["Certification"] = Relationship(
        back_populates="products", link_model=ProductCertificationLink
    )
    faqs: List["FAQItem"] = Relationship(
        back_populates="products", link_model=ProductFAQLink
    )
    comparison_topics: List["ComparisonTopic"] = Relationship(
        back_populates="products", link_model=ProductComparisonLink
    )
    assets: List["ContentAsset"] = Relationship(back_populates="product")
    alternative_products: List["Product"] = Relationship(
        back_populates="alternative_products",
        link_model=AlternativePartLink,
        sa_relationship_kwargs={
            "primaryjoin": "Product.id == AlternativePartLink.product_id",
            "secondaryjoin": "Product.id == AlternativePartLink.alternative_product_id",
            "lazy": "select",
        },
    )
