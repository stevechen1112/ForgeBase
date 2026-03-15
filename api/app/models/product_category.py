import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.core.datetime import utcnow_naive

if TYPE_CHECKING:
    from app.models.product import Product


class ProductCategory(SQLModel, table=True):
    __tablename__ = "product_categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    category_name: str = Field(max_length=60)
    slug: str = Field(max_length=60, unique=True, index=True)
    description: Optional[str] = Field(default=None)  # richtext stored as HTML string
    image_url: Optional[str] = Field(default=None)
    parent_id: Optional[uuid.UUID] = Field(default=None, foreign_key="product_categories.id")
    sort_order: int = Field(default=0)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: str = Field(default="draft")  # draft / published
    locale: str = Field(default="en", max_length=5)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)

    # Relationships
    children: List["ProductCategory"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[ProductCategory.parent_id]"}
    )
    products: List["Product"] = Relationship(back_populates="category")
