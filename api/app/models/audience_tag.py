import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from sqlmodel import SQLModel, Field


class AudienceTag(SQLModel, table=True):
    """
    Named audience tags for segmentation (spec 1b.2.5).
    e.g. "hydraulic-seal-interest", "high-intent-visitor"
    """
    __tablename__ = "audience_tags"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=80, unique=True, index=True)
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
        foreign_key="visitors.visitor_id", primary_key=True
    )
    tag_id: uuid.UUID = Field(
        foreign_key="audience_tags.id", primary_key=True
    )
    tagged_at: datetime = Field(default_factory=utcnow_naive)
    tagged_by: str = Field(default="manual", max_length=20)
    # "manual" | "system"
