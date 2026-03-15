"""
Account model — 2.1.2 IP-to-Company identification.

An Account represents a company identified through IP-to-company lookup.
Visitors can be associated with an Account after IP resolution.
"""
import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class Account(SQLModel, table=True):
    """
    Company-level account resolved from visitor IP address.
    Linked via Visitor.account_id after IP enrichment.
    """
    __tablename__ = "accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Company identity
    company_name: str = Field(max_length=200, index=True)
    domain: Optional[str] = Field(default=None, max_length=200, index=True)

    # Enrichment fields (from Clearbit / 6sense / manual)
    industry: Optional[str] = Field(default=None, max_length=100)
    employee_count_range: Optional[str] = Field(default=None, max_length=30)
    # e.g. "1-10", "11-50", "51-200", "201-500", "501-1000", "1001+"
    annual_revenue_range: Optional[str] = Field(default=None, max_length=30)
    # e.g. "<1M", "1M-10M", "10M-50M", "50M+"
    country: Optional[str] = Field(default=None, max_length=2)  # ISO 3166-1
    city: Optional[str] = Field(default=None, max_length=100)
    linkedin_url: Optional[str] = Field(default=None, max_length=500)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None)

    # Enrichment source & metadata
    enrichment_source: Optional[str] = Field(default=None, max_length=50)
    # "clearbit" | "6sense" | "manual" | "ip_api"
    enrichment_status: str = Field(default="pending", max_length=20)
    # "pending" | "enriched" | "failed" | "not_found"
    last_enriched_at: Optional[datetime] = Field(default=None)

    # Account-level intent aggregation
    total_visitors: int = Field(default=0)
    total_page_views: int = Field(default=0)
    max_intent_score: int = Field(default=0)
    # Highest intent score among all associated visitors

    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
