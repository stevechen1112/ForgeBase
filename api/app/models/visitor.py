import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class Visitor(SQLModel, table=True):
    """
    Anonymous visitor identified by first-party cookie visitor_id.
    One record per unique visitor. Accumulates intent score over time.
    Spec: 12.6 (intent scoring), 1b.2.1
    """
    __tablename__ = "visitors"

    visitor_id: uuid.UUID = Field(primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    # visitor_id is generated client-side and stored in first-party cookie

    first_seen: datetime = Field(default_factory=utcnow_naive)
    last_seen: datetime = Field(default_factory=utcnow_naive)
    last_activity_at: datetime = Field(default_factory=utcnow_naive)

    total_visits: int = Field(default=1)
    total_page_views: int = Field(default=0)

    # Intent scoring (spec 12.6.3)
    intent_score: int = Field(default=0, index=True)
    intent_stage: str = Field(default="cold", max_length=20, index=True)    # "cold" | "warm" | "hot" | "sales_ready"

    # Intent Score 2.0 — 採購 facets（實效計畫 §4.1）
    facet_product_interest: int = Field(default=0, index=True)
    facet_trust_validation: int = Field(default=0, index=True)
    facet_procurement_readiness: int = Field(default=0, index=True)
    facet_urgency: int = Field(default=0, index=True)
    intent_explanation: Optional[str] = Field(default=None)     # 「為何 Hot」顧問可讀字串

    # Device & location (server-side enrichment)
    device_type: Optional[str] = Field(default=None, max_length=20)
    # "desktop" | "mobile" | "tablet"
    country: Optional[str] = Field(default=None, max_length=2)
    # ISO 3166-1 alpha-2

    # Identity: linked contact after form submission
    contact_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="contacts.id",
        ondelete="SET NULL",
        index=True,
    )

    # Analytics consent lifecycle. Detailed audit uses a keyed hash rather
    # than retaining the raw anonymous browser identifier.
    analytics_consent_status: str = Field(default="unknown", max_length=20, index=True)
    consent_updated_at: Optional[datetime] = Field(default=None)

    # Stage change alert flags
    stage_alert_sent: bool = Field(default=False)
    # Reset when stage changes, set after alert is sent

    # ML Intent Scoring (3.2.1 / 3.2.2) — predicted conversion probability from ML model
    ml_intent_score: Optional[float] = Field(default=None)
    # 0.0 – 1.0 probability; None until ML model has been run
    ml_score_updated_at: Optional[datetime] = Field(default=None)

    is_test_data: bool = Field(default=False, index=True)
    test_run_id: Optional[str] = Field(default=None, max_length=100)

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
