import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class Segment(SQLModel, table=True):
    """
    Saved audience segment definition.
    Conditions are evaluated against the Visitor table.
    Spec: 2.1.1 Advanced Audience Segmentation
    """
    __tablename__ = "segments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, index=True)
    description: str = Field(default="", max_length=300)

    # JSON array of condition objects (see README for schema)
    # Each condition: {"type": "intent_stage"|"intent_score"|"event_count"|"tag"|"country",
    #                  "op": "eq"|"gte"|"lte"|"in",
    #                  "value": ..., "event_name": ..., "within_days": ..., "tag_id": ...}
    conditions: str = Field(default="[]")

    # "AND" | "OR"
    combinator: str = Field(default="AND", max_length=3)

    created_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
