from typing import Optional
from pydantic import BaseModel, Field


class SiteProfileRead(BaseModel):
    """Public read schema — returned by GET /api/v1/site-profile."""

    brand_name: str
    logo_mark: str
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    theme_key: str
    layout_key: str
    contact_email: str
    contact_phone: Optional[str] = None
    site_url: str
    default_locale: str
    asset_base: Optional[str] = None
    demo_company_folder: Optional[str] = None
    header_nav_json: Optional[str] = None
    header_actions_json: Optional[str] = None
    footer_sections_json: Optional[str] = None
    footer_badges_json: Optional[str] = None
    social_links_json: Optional[str] = None
    footer_cta_title: Optional[str] = None
    footer_cta_description: Optional[str] = None
    footer_cta_label: Optional[str] = None
    footer_cta_href: Optional[str] = None
    asset_manifest_json: Optional[str] = None

    model_config = {"from_attributes": True}


class SiteProfileUpdate(BaseModel):
    """Admin update schema — accepted by PUT /api/v1/site-profile."""

    brand_name: Optional[str] = Field(default=None, max_length=120)
    logo_mark: Optional[str] = Field(default=None, max_length=10)
    logo_url: Optional[str] = Field(default=None, max_length=500)
    favicon_url: Optional[str] = Field(default=None, max_length=500)
    theme_key: Optional[str] = Field(default=None, max_length=30)
    layout_key: Optional[str] = Field(default=None, max_length=30)
    contact_email: Optional[str] = Field(default=None, max_length=200)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    site_url: Optional[str] = Field(default=None, max_length=500)
    default_locale: Optional[str] = Field(default=None, max_length=5)
    asset_base: Optional[str] = Field(default=None, max_length=500)
    demo_company_folder: Optional[str] = Field(default=None, max_length=120)
    header_nav_json: Optional[str] = None
    header_actions_json: Optional[str] = None
    footer_sections_json: Optional[str] = None
    footer_badges_json: Optional[str] = None
    social_links_json: Optional[str] = None
    footer_cta_title: Optional[str] = Field(default=None, max_length=200)
    footer_cta_description: Optional[str] = None
    footer_cta_label: Optional[str] = Field(default=None, max_length=120)
    footer_cta_href: Optional[str] = Field(default=None, max_length=500)
    asset_manifest_json: Optional[str] = None
