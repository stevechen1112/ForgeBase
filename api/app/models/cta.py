import uuid
from datetime import datetime
from app.core.datetime import utcnow_naive
from typing import Optional
from sqlmodel import SQLModel, Field


class CTA(SQLModel, table=True):
    """Call-to-Action blocks — reusable across pages/products/applications."""
    __tablename__ = "ctas"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    cta_key: str = Field(max_length=60, unique=True, index=True)    # machine name, e.g. "get_quote_banner"
    cta_type: str = Field(max_length=30)    # "banner" | "inline" | "popup" | "sticky_bar"
    headline: str = Field(max_length=120)
    subheadline: Optional[str] = Field(default=None, max_length=240)
    button_label: str = Field(max_length=60)
    button_action: str = Field(max_length=30)   # "open_rfq" | "link" | "download"
    button_url: Optional[str] = Field(default=None, max_length=500)
    bg_color: Optional[str] = Field(default=None, max_length=20)    # hex eg "#1A56DB"
    image_url: Optional[str] = Field(default=None, max_length=500)
    locale: str = Field(default="en", max_length=5)
    status: str = Field(default="active", max_length=20)
    sort_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
