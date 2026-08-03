"""
回覆範本庫（實效計畫 §5.4）

依產品線／國家／語系維護的第一封回覆範本，
供 reply-assist 依 RFQ 買家條件匹配。
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class ReplyTemplate(SQLModel, table=True):
    __tablename__ = "reply_templates"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    name: str = Field(max_length=120)
    product_line: Optional[str] = Field(default=None, max_length=80)
    country: Optional[str] = Field(default=None, max_length=2)   # ISO alpha-2；None = 通用
    locale: str = Field(default="en", max_length=5)
    body: str = Field()
    created_at: datetime = Field(default_factory=utcnow_naive)
    updated_at: datetime = Field(default_factory=utcnow_naive)
