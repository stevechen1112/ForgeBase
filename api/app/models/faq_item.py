import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from app.models.associations import ProductFAQLink, ApplicationFAQLink

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.application import Application


class FAQItem(SQLModel, table=True):
    __tablename__ = "faq_items"
    __table_args__ = (
        UniqueConstraint(
            "variant_key", "locale", "tenant_id",
            name="uq_faq_items_variant_key_locale_tenant",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    # Stable key shared across locale variants of the same FAQ
    variant_key: str = Field(default_factory=lambda: f"faq-{uuid.uuid4().hex[:16]}", max_length=80, index=True)
    question: str = Field(max_length=300)
    answer: str = Field()          # richtext / markdown
    category_tag: Optional[str] = Field(default=None, max_length=60)
    locale: str = Field(default="en", max_length=5)
    sort_order: int = Field(default=0)
    status: str = Field(default="draft", max_length=20)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)

    # Relationships
    products: List["Product"] = Relationship(
        back_populates="faqs", link_model=ProductFAQLink
    )
    applications: List["Application"] = Relationship(
        back_populates="faqs", link_model=ApplicationFAQLink
    )
