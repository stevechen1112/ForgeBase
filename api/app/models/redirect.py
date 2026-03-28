import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field
from app.core.datetime import utcnow_naive


class Redirect(SQLModel, table=True):
    """
    301/302 redirect rules for SEO slug migrations.
    When a product/category/page slug changes, insert a row here to
    preserve inbound links and Google ranking signals.

    Examples:
      from_path="/products/tools/old-slug"  → to_path="/products/tools/new-slug"
      from_path="/old-category"             → to_path="/products/new-category"
    """
    __tablename__ = "redirects"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    from_path: str = Field(max_length=500, unique=True, index=True)
    # e.g. "/products/old-slug" — always starts with /
    to_path: str = Field(max_length=500)
    # e.g. "/products/new-slug"
    status_code: int = Field(default=301)
    # 301 = permanent (SEO juice passes), 302 = temporary
    is_active: bool = Field(default=True, index=True)
    note: str = Field(default="", max_length=255)
    # optional human note, e.g. "slug change 2026-03 campaign"
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
