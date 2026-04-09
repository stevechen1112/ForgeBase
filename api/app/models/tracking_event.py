import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class TrackingEvent(SQLModel, table=True):
    """
    Immutable event log. Append-only — never updated or deleted.
    Stores all 15 events from spec 12.5 with their shared + specific properties.
    Spec: 12.5.2, 12.5.4
    """
    __tablename__ = "tracking_events"

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    event_name: str = Field(max_length=50, index=True)
    # 15 valid values from spec 12.5.1

    timestamp: datetime = Field(
        default_factory=utcnow_naive,
        index=True,
    )

    # Session & visitor context
    session_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="tracking_sessions.session_id", index=True
    )
    visitor_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="visitors.visitor_id", index=True
    )

    # Page context
    page_url: Optional[str] = Field(default=None, max_length=500)
    page_type: Optional[str] = Field(default=None, max_length=40)
    page_id: Optional[uuid.UUID] = Field(default=None)
    locale: Optional[str] = Field(default="en", max_length=5)

    # Traffic attribution
    referrer: Optional[str] = Field(default=None, max_length=500)
    traffic_source: Optional[str] = Field(default=None, max_length=30)
    campaign_id: Optional[str] = Field(default=None, max_length=200)

    # Client context (partially enriched server-side)
    user_agent: Optional[str] = Field(default=None, max_length=300)
    device_type: Optional[str] = Field(default=None, max_length=20)
    country: Optional[str] = Field(default=None, max_length=2)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    # Stored for GeoIP; not exposed in API responses

    # Event-specific payload (JSON string — spec 12.5.3)
    properties: Optional[str] = Field(default=None)

    # Intent score delta applied by this event (for audit trail)
    score_delta: int = Field(default=0)
