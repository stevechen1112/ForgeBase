from typing import Any, Optional

from pydantic import BaseModel


class APIResponse(BaseModel):
    data: Any = None
    meta: Optional[Any] = None


class APIError(BaseModel):
    error: str
    detail: Optional[str] = None


class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
