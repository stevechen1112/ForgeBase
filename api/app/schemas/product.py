import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    product_name: str = Field(max_length=100)
    slug: str = Field(max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    model_number: str = Field(max_length=50)
    short_description: str = Field(max_length=200)
    full_description: Optional[str] = None
    specifications: Optional[str] = None   # JSON string
    category_id: uuid.UUID
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: str = Field(default="draft")
    locale: str = Field(default="en", max_length=5)
    is_featured: bool = Field(default=False)
    display_priority: int = Field(default=0)


class ProductUpdate(BaseModel):
    product_name: Optional[str] = Field(default=None, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    model_number: Optional[str] = Field(default=None, max_length=50)
    short_description: Optional[str] = Field(default=None, max_length=200)
    full_description: Optional[str] = None
    specifications: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: Optional[str] = None
    locale: Optional[str] = Field(default=None, max_length=5)
    published_at: Optional[datetime] = None
    is_featured: Optional[bool] = None
    display_priority: Optional[int] = None


class ProductRead(BaseModel):
    id: uuid.UUID
    product_name: str
    slug: str
    model_number: str
    short_description: str
    full_description: Optional[str]
    specifications: Optional[str]
    category_id: uuid.UUID
    seo_title: Optional[str]
    seo_description: Optional[str]
    status: str
    locale: str
    is_featured: bool
    display_priority: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}
