import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class SiteProfile(SQLModel, table=True):
    """Per-site branding and theme configuration.

    Each deployed ForgeBase site owns one row. The frontend reads these
    values (via the /api/v1/site-profile endpoint) to configure brand
    name, logo, contact details, and the CSS theme preset.
    """

    __tablename__ = "site_profiles"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # ── Branding ──
    brand_name: str = Field(max_length=120, default="NorthForge Tools")
    logo_mark: str = Field(max_length=10, default="NF")
    logo_url: Optional[str] = Field(default=None, max_length=500)
    favicon_url: Optional[str] = Field(default=None, max_length=500)

    # ── Theme ──
    theme_key: str = Field(max_length=30, default="cobalt")

    # ── Contact ──
    contact_email: str = Field(max_length=200, default="sales@northforgetools.com")
    contact_phone: Optional[str] = Field(default=None, max_length=50)

    # ── SEO / URL ──
    site_url: str = Field(max_length=500, default="https://example.com")
    default_locale: str = Field(max_length=5, default="en")

    # ── Asset base ──
    asset_base: Optional[str] = Field(default=None, max_length=500)
    demo_company_folder: Optional[str] = Field(default=None, max_length=120)

    # ── Timestamps ──
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
