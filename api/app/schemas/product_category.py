import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── ProductCategory schemas ──────────────────────────────────────────────────

class ProductCategoryCreate(BaseModel):
    category_name: str = Field(max_length=60)
    slug: str = Field(max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[uuid.UUID] = None
    sort_order: int = Field(default=0, ge=0)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: str = Field(default="draft")
    locale: str = Field(default="en", max_length=5)


class ProductCategoryUpdate(BaseModel):
    category_name: Optional[str] = Field(default=None, max_length=60)
    slug: Optional[str] = Field(default=None, max_length=60, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: Optional[str] = None
    image_url: Optional[str] = Field(default=None, max_length=500)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[uuid.UUID] = None
    sort_order: Optional[int] = Field(default=None, ge=0)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: Optional[str] = None
    locale: Optional[str] = Field(default=None, max_length=5)


class ProductCategoryRead(BaseModel):
    id: uuid.UUID
    category_name: str
    slug: str
    description: Optional[str]
    image_url: Optional[str]
    og_image_url: Optional[str]
    parent_id: Optional[uuid.UUID]
    sort_order: int
    seo_title: Optional[str]
    seo_description: Optional[str]
    status: str
    locale: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductCategoryTree(ProductCategoryRead):
    """Nested tree representation for hierarchical display."""
    children: List["ProductCategoryTree"] = []

    model_config = {"from_attributes": True}
