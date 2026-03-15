import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class Visitor(SQLModel, table=True):
    """
    Anonymous visitor identified by first-party cookie visitor_id.
    One record per unique visitor. Accumulates intent score over time.
    Spec: 12.6 (intent scoring), 1b.2.1
    """
    __tablename__ = "visitors"

    visitor_id: uuid.UUID = Field(primary_key=True)
    # visitor_id is generated client-side and stored in first-party cookie

    first_seen: datetime = Field(default_factory=utcnow_naive)
    last_seen: datetime = Field(default_factory=utcnow_naive)
    last_activity_at: datetime = Field(default_factory=utcnow_naive)

    total_visits: int = Field(default=1)
    total_page_views: int = Field(default=0)

    # Intent scoring (spec 12.6.3)
    intent_score: int = Field(default=0)
    intent_stage: str = Field(default="cold", max_length=20)
    # "cold" | "warm" | "hot" | "sales_ready"

    # Device & location (server-side enrichment)
    device_type: Optional[str] = Field(default=None, max_length=20)
    # "desktop" | "mobile" | "tablet"
    country: Optional[str] = Field(default=None, max_length=2)
    # ISO 3166-1 alpha-2

    # Identity: linked contact after form submission
    contact_id: Optional[uuid.UUID] = Field(default=None, foreign_key="contacts.id")

    # IP-to-Company: linked account after IP resolution (2.1.2)
    account_id: Optional[uuid.UUID] = Field(default=None, foreign_key="accounts.id", index=True)
    last_seen_ip: Optional[str] = Field(default=None, max_length=45)
    ip_resolved_at: Optional[datetime] = Field(default=None)

    # Stage change alert flags
    stage_alert_sent: bool = Field(default=False)
    # Reset when stage changes, set after alert is sent

    # ML Intent Scoring (3.2.1 / 3.2.2) — predicted conversion probability from ML model
    ml_intent_score: Optional[float] = Field(default=None)
    # 0.0 – 1.0 probability; None until ML model has been run
    ml_score_updated_at: Optional[datetime] = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
