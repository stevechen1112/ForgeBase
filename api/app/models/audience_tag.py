import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class AudienceTag(SQLModel, table=True):
    """
    Named audience tags for segmentation (spec 1b.2.5).
    e.g. "hydraulic-seal-viewers", "recent-catalog-downloaders"
    """
    __tablename__ = "audience_tags"
    __table_args__ = (UniqueConstraint("name", name="uq_audience_tags_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=80)
    description: str = Field(default="", max_length=200)
    # Rule type: manual vs automatic
    rule_type: str = Field(default="manual", max_length=20)
    # "manual" | "auto_rule"
    rule_config: str = Field(default="{}")
    # JSON: {"event_name": "product_view", "min_count": 3, "within_days": 30}
    created_at: datetime = Field(default_factory=utcnow_naive)


class VisitorTagLink(SQLModel, table=True):
    """M2M: Visitor ↔ AudienceTag"""
    __tablename__ = "visitor_tag_links"
    visitor_id: uuid.UUID = Field(
        foreign_key="visitors.visitor_id", ondelete="CASCADE", primary_key=True
    )
    tag_id: uuid.UUID = Field(
        foreign_key="audience_tags.id", ondelete="CASCADE", primary_key=True
    )
    tagged_at: datetime = Field(default_factory=utcnow_naive)
    tagged_by: str = Field(default="manual", max_length=20)
    # "manual" | "system"
