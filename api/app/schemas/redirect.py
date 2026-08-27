import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class RedirectCreate(BaseModel):
    from_path: str = Field(max_length=500)
    to_path: str = Field(max_length=500)
    status_code: int = Field(default=301)
    is_active: bool = Field(default=True)
    note: str = Field(default="", max_length=255)

    @field_validator("from_path", "to_path")
    @classmethod
    def must_start_with_slash(cls, v: str) -> str:
        if not v.startswith("/"):
            raise ValueError("Path must start with /")
        return v

    @field_validator("status_code")
    @classmethod
    def valid_status_code(cls, v: int) -> int:
        if v not in (301, 302):
            raise ValueError("status_code must be 301 or 302")
        return v


class RedirectUpdate(BaseModel):
    from_path: Optional[str] = Field(default=None, max_length=500)
    to_path: Optional[str] = Field(default=None, max_length=500)
    status_code: Optional[int] = None
    is_active: Optional[bool] = None
    note: Optional[str] = Field(default=None, max_length=255)

    @field_validator("from_path", "to_path", mode="before")
    @classmethod
    def must_start_with_slash(cls, v: object) -> object:
        if isinstance(v, str) and not v.startswith("/"):
            raise ValueError("Path must start with /")
        return v

    @field_validator("status_code", mode="before")
    @classmethod
    def valid_status_code(cls, v: object) -> object:
        if v is not None and v not in (301, 302):
            raise ValueError("status_code must be 301 or 302")
        return v


class RedirectRead(BaseModel):
    id: uuid.UUID
    from_path: str
    to_path: str
    status_code: int
    is_active: bool
    note: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
