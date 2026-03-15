"""
2.5.4 A/B Test 模型

ABTest     — 每個測試定義（頁面 + 兩個 variant 內容）
ABTestView — 每次曝光 / 互動紀錄（用於計算 CTR 差異）
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ABTest(SQLModel, table=True):
    __tablename__ = "ab_tests"

    id: _uuid.UUID = Field(
        default_factory=_uuid.uuid4,
        primary_key=True,
        index=True,
    )

    # 識別
    name: str = Field(index=True)                    # 可讀名稱，e.g. "Homepage CTA 測試 #1"
    description: Optional[str] = None

    # 測試對象
    page_id: Optional[_uuid.UUID] = Field(default=None, index=True)
    test_element: str = "cta"                        # "cta" | "headline" | "block" | "custom"

    # Variant 內容（JSON-string or plain text）
    variant_a: str = ""                              # Control
    variant_b: str = ""                              # Challenger

    # 分流比例 0.0–1.0，預設 50/50
    split_ratio: float = Field(default=0.5)          # 0.5 = 50% see variant_b

    is_active: bool = Field(default=True, index=True)

    # 統計快取（定期更新，不做 realtime join）
    views_a: int = Field(default=0)
    views_b: int = Field(default=0)
    conversions_a: int = Field(default=0)
    conversions_b: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ABTestView(SQLModel, table=True):
    """每次 variant 曝光或轉換事件。"""
    __tablename__ = "ab_test_views"

    id: int = Field(default=None, primary_key=True)

    test_id: _uuid.UUID = Field(index=True)
    visitor_id: Optional[str] = Field(default=None, index=True)  # anonymous fingerprint
    variant: str = ""                                # "a" | "b"
    converted: bool = Field(default=False)
    user_agent: Optional[str] = None
    referrer: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
