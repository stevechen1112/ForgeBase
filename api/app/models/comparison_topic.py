import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.models.associations import ProductComparisonLink

if TYPE_CHECKING:
    from app.models.product import Product


class ComparisonTopic(SQLModel, table=True):
    """Competitive comparison topics — e.g. 'vs Steel Rivets' with dimension breakdown."""
    __tablename__ = "comparison_topics"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    topic_title: str = Field(max_length=120, index=True)
    slug: str = Field(max_length=120, unique=True, index=True)
    summary: Optional[str] = Field(default=None, max_length=500)
    dimensions: Optional[str] = Field(default=None)
    # JSON: [{"dimension": "Cost", "our_value": "Low", "competitor_value": "High", "winner": "us"}]
    conclusion: Optional[str] = Field(default=None)  # richtext
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
        back_populates="comparison_topics", link_model=ProductComparisonLink
    )
