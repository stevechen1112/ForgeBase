import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

from app.core.datetime import utcnow_naive
from app.models.associations import ProductCertificationLink

if TYPE_CHECKING:
    from app.models.product import Product


class Certification(SQLModel, table=True):
    __tablename__ = "certifications"
    __table_args__ = (
        UniqueConstraint("slug", "locale", "tenant_id", name="uq_certifications_slug_locale_tenant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    cert_name: str = Field(max_length=100, index=True)   # e.g. "ISO 9001", "RoHS"
    slug: str = Field(max_length=120, index=True)
    issuer: Optional[str] = Field(default=None, max_length=120)
    cert_number: Optional[str] = Field(default=None, max_length=80)
    issued_at: Optional[datetime] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    description: Optional[str] = Field(default=None)    # richtext
    badge_image_url: Optional[str] = Field(default=None, max_length=500)
    document_url: Optional[str] = Field(default=None, max_length=500)  # PDF link
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="active", max_length=20)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)

    # Relationships
    products: List["Product"] = Relationship(
        back_populates="certifications", link_model=ProductCertificationLink
    )
