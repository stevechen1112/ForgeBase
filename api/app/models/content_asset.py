import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.core.datetime import utcnow_naive

if TYPE_CHECKING:
    from app.models.product import Product


class ContentAsset(SQLModel, table=True):
    """
    Upload records for images, PDFs, CAD files, etc.
    Stored in Cloudflare R2; this table keeps metadata.
    """
    __tablename__ = "content_assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True)
    original_filename: str = Field(max_length=255)
    r2_key: str = Field(max_length=500, unique=True)   # path in R2 bucket
    public_url: str = Field(max_length=500)
    mime_type: str = Field(max_length=80)
    file_size_bytes: int = Field(default=0)
    asset_type: str = Field(max_length=30)
    # "image" | "pdf" | "cad" | "video" | "other"
    alt_text: Optional[str] = Field(default=None, max_length=200)
    title: Optional[str] = Field(default=None, max_length=200)
    # 2.3.2 PDF indexing
    is_indexable: bool = Field(default=False)
    seo_title: Optional[str] = Field(default=None, max_length=200)
    product_id: Optional[uuid.UUID] = Field(default=None, foreign_key="products.id")
    page_id: Optional[uuid.UUID] = Field(default=None, foreign_key="pages.id")
    uploaded_by: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow_naive)

    # Relationships
    product: Optional["Product"] = Relationship(back_populates="assets")
