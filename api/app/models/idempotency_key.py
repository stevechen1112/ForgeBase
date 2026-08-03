"""
Idempotency-Key 紀錄（CF→FB Publish Contract §6）

讓帶 `Idempotency-Key` header 的 POST 重送時回傳首次結果，
避免網路重試造成重複建頁。
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.core.datetime import utcnow_naive


class IdempotencyKey(SQLModel, table=True):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint("tenant_id", "endpoint", "key", name="uq_idempotency_tenant_endpoint_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: Optional[uuid.UUID] = Field(default=None, foreign_key="tenants.id", index=True)
    endpoint: str = Field(max_length=200)   # e.g. "POST /content/pages"
    key: str = Field(max_length=255)
    status_code: int = Field(default=201)
    response_json: str = Field()            # 首次成功回應的 JSON 字串
    created_at: datetime = Field(default_factory=utcnow_naive)
