import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ApplicationCreate(BaseModel):
    application_name: str = Field(max_length=100)
    slug: str = Field(max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    industry: str = Field(max_length=60)
    description: Optional[str] = None
    challenge: Optional[str] = None
    solution: Optional[str] = None
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: str = Field(default="draft")
    locale: str = Field(default="en", max_length=5)
    sort_order: int = Field(default=0, ge=0)


class ApplicationUpdate(BaseModel):
    application_name: Optional[str] = Field(default=None, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    industry: Optional[str] = Field(default=None, max_length=60)
    description: Optional[str] = None
    challenge: Optional[str] = None
    solution: Optional[str] = None
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: Optional[str] = None
    locale: Optional[str] = Field(default=None, max_length=5)
    sort_order: Optional[int] = Field(default=None, ge=0)


class ApplicationRead(BaseModel):
    id: uuid.UUID
    application_name: str
    slug: str
    industry: str
    description: Optional[str]
    challenge: Optional[str]
    solution: Optional[str]
    hero_image_url: Optional[str]
    og_image_url: Optional[str]
    seo_title: Optional[str]
    seo_description: Optional[str]
    status: str
    locale: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── FAQItem schemas ───────────────────────────────────────────────────────────

class FAQItemCreate(BaseModel):
    question: str = Field(max_length=300)
    answer: str
    category_tag: Optional[str] = Field(default=None, max_length=60)
    locale: str = Field(default="en", max_length=5)
    sort_order: int = Field(default=0, ge=0)
    status: str = Field(default="draft")
    variant_key: Optional[str] = Field(default=None, max_length=80)


class FAQItemUpdate(BaseModel):
    question: Optional[str] = Field(default=None, max_length=300)
    answer: Optional[str] = None
    category_tag: Optional[str] = Field(default=None, max_length=60)
    locale: Optional[str] = Field(default=None, max_length=5)
    sort_order: Optional[int] = Field(default=None, ge=0)
    status: Optional[str] = None
    variant_key: Optional[str] = Field(default=None, max_length=80)


class FAQItemRead(BaseModel):
    id: uuid.UUID
    variant_key: str
    question: str
    answer: str
    category_tag: Optional[str]
    locale: str
    sort_order: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── ComparisonTopic schemas ───────────────────────────────────────────────────

class ComparisonTopicCreate(BaseModel):
    topic_title: str = Field(max_length=120)
    slug: str = Field(max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    summary: Optional[str] = Field(default=None, max_length=500)
    dimensions: Optional[str] = None   # JSON
    conclusion: Optional[str] = None
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: str = Field(default="draft")
    locale: str = Field(default="en", max_length=5)
    sort_order: int = Field(default=0, ge=0)


class ComparisonTopicUpdate(BaseModel):
    topic_title: Optional[str] = Field(default=None, max_length=120)
    slug: Optional[str] = Field(default=None, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    summary: Optional[str] = Field(default=None, max_length=500)
    dimensions: Optional[str] = None
    conclusion: Optional[str] = None
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    status: Optional[str] = None
    locale: Optional[str] = Field(default=None, max_length=5)
    sort_order: Optional[int] = Field(default=None, ge=0)


class ComparisonTopicRead(BaseModel):
    id: uuid.UUID
    topic_title: str
    slug: str
    summary: Optional[str]
    dimensions: Optional[str]
    conclusion: Optional[str]
    seo_title: Optional[str]
    seo_description: Optional[str]
    status: str
    locale: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Certification schemas ─────────────────────────────────────────────────────

class CertificationCreate(BaseModel):
    cert_name: str = Field(max_length=100)
    slug: Optional[str] = Field(default=None, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    issuer: Optional[str] = Field(default=None, max_length=120)
    cert_number: Optional[str] = Field(default=None, max_length=80)
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    badge_image_url: Optional[str] = Field(default=None, max_length=500)
    document_url: Optional[str] = Field(default=None, max_length=500)
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="active")


class CertificationUpdate(BaseModel):
    cert_name: Optional[str] = Field(default=None, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    issuer: Optional[str] = Field(default=None, max_length=120)
    cert_number: Optional[str] = Field(default=None, max_length=80)
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    badge_image_url: Optional[str] = Field(default=None, max_length=500)
    document_url: Optional[str] = Field(default=None, max_length=500)
    locale: Optional[str] = Field(default=None, max_length=5)
    status: Optional[str] = None


class CertificationRead(BaseModel):
    id: uuid.UUID
    cert_name: str
    slug: str
    issuer: Optional[str]
    cert_number: Optional[str]
    issued_at: Optional[datetime]
    expires_at: Optional[datetime]
    description: Optional[str]
    badge_image_url: Optional[str]
    document_url: Optional[str]
    locale: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Capability schemas ────────────────────────────────────────────────────────

class CapabilityCreate(BaseModel):
    capability_name: str = Field(max_length=100)
    slug: str = Field(max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    icon_url: Optional[str] = Field(default=None, max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=500)
    short_description: str = Field(max_length=200)
    detail: Optional[str] = None
    metrics: Optional[str] = None   # JSON
    category_tag: Optional[str] = Field(default=None, max_length=60)
    sort_order: int = Field(default=0, ge=0)
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="draft")


class CapabilityUpdate(BaseModel):
    capability_name: Optional[str] = Field(default=None, max_length=100)
    slug: Optional[str] = Field(default=None, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    icon_url: Optional[str] = Field(default=None, max_length=500)
    image_url: Optional[str] = Field(default=None, max_length=500)
    short_description: Optional[str] = Field(default=None, max_length=200)
    detail: Optional[str] = None
    metrics: Optional[str] = None
    category_tag: Optional[str] = Field(default=None, max_length=60)
    sort_order: Optional[int] = Field(default=None, ge=0)
    locale: Optional[str] = Field(default=None, max_length=5)
    status: Optional[str] = None


class CapabilityRead(BaseModel):
    id: uuid.UUID
    capability_name: str
    slug: str
    icon_url: Optional[str]
    image_url: Optional[str]
    short_description: str
    detail: Optional[str]
    metrics: Optional[str]
    category_tag: Optional[str]
    sort_order: int
    locale: str
    status: str
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── CTA schemas ───────────────────────────────────────────────────────────────

class CTACreate(BaseModel):
    cta_key: str = Field(max_length=60)
    cta_type: str = Field(max_length=30)
    headline: str = Field(max_length=120)
    subheadline: Optional[str] = Field(default=None, max_length=240)
    button_label: str = Field(max_length=60)
    button_action: str = Field(max_length=30)
    button_url: Optional[str] = Field(default=None, max_length=500)
    bg_color: Optional[str] = Field(default=None, max_length=20)
    image_url: Optional[str] = Field(default=None, max_length=500)
    locale: str = Field(default="en", max_length=5)
    status: Literal["draft", "published", "archived"] = "draft"
    sort_order: int = Field(default=0, ge=0)


class CTAUpdate(BaseModel):
    cta_key: Optional[str] = Field(default=None, max_length=60)
    cta_type: Optional[str] = Field(default=None, max_length=30)
    headline: Optional[str] = Field(default=None, max_length=120)
    subheadline: Optional[str] = Field(default=None, max_length=240)
    button_label: Optional[str] = Field(default=None, max_length=60)
    button_action: Optional[str] = Field(default=None, max_length=30)
    button_url: Optional[str] = Field(default=None, max_length=500)
    bg_color: Optional[str] = Field(default=None, max_length=20)
    image_url: Optional[str] = Field(default=None, max_length=500)
    locale: Optional[str] = Field(default=None, max_length=5)
    status: Optional[Literal["draft", "published", "archived"]] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


class CTARead(BaseModel):
    id: uuid.UUID
    cta_key: str
    cta_type: str
    headline: str
    subheadline: Optional[str]
    button_label: str
    button_action: str
    button_url: Optional[str]
    bg_color: Optional[str]
    image_url: Optional[str]
    locale: str
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Page schemas ──────────────────────────────────────────────────────────────

class PageCreate(BaseModel):
    page_type: str = Field(max_length=40)
    slug: str = Field(max_length=120, pattern=r"^[a-z0-9]+(?:[/-][a-z0-9]+)*$")
    title: str = Field(max_length=120)
    subtitle: Optional[str] = Field(default=None, max_length=240)
    body: Optional[str] = None
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    structured_data: Optional[str] = None
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="draft")
    noindex: bool = False
    entity_type: Optional[str] = Field(default=None, max_length=40)
    entity_id: Optional[uuid.UUID] = None


class PageUpdate(BaseModel):
    page_type: Optional[str] = Field(default=None, max_length=40)
    slug: Optional[str] = Field(default=None, max_length=120)
    title: Optional[str] = Field(default=None, max_length=120)
    subtitle: Optional[str] = Field(default=None, max_length=240)
    body: Optional[str] = None
    hero_image_url: Optional[str] = Field(default=None, max_length=500)
    seo_title: Optional[str] = Field(default=None, max_length=70)
    seo_description: Optional[str] = Field(default=None, max_length=160)
    og_image_url: Optional[str] = Field(default=None, max_length=500)
    canonical_url: Optional[str] = Field(default=None, max_length=500)
    structured_data: Optional[str] = None
    locale: Optional[str] = Field(default=None, max_length=5)
    status: Optional[str] = None
    noindex: Optional[bool] = None
    entity_type: Optional[str] = Field(default=None, max_length=40)
    entity_id: Optional[uuid.UUID] = None


class PageRead(BaseModel):
    id: uuid.UUID
    page_type: str
    slug: str
    title: str
    subtitle: Optional[str]
    body: Optional[str]
    hero_image_url: Optional[str]
    seo_title: Optional[str]
    seo_description: Optional[str]
    og_image_url: Optional[str]
    canonical_url: Optional[str]
    structured_data: Optional[str]
    locale: str
    status: str
    noindex: bool
    entity_type: Optional[str]
    entity_id: Optional[uuid.UUID]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    model_config = {"from_attributes": True}

