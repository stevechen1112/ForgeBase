import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, field_validator


VALID_CONTEXT_TYPES = {"product", "faq", "home", "category", "application", "unknown"}
VALID_SUGGESTED_ACTIONS = {"none", "rfq", "contact"}


class ChatSessionCreate(BaseModel):
    visitor_id: uuid.UUID
    session_id: Optional[uuid.UUID] = None
    context_page: Optional[str] = None
    context_entity_type: str = "unknown"
    context_entity_id: Optional[uuid.UUID] = None
    locale: str = "en"

    @field_validator("context_entity_type")
    @classmethod
    def validate_context_entity_type(cls, value: str) -> str:
        if value not in VALID_CONTEXT_TYPES:
            return "unknown"
        return value


class ChatSource(BaseModel):
    type: str
    id: str
    name: str
    url: Optional[str] = None


class ChatSessionCreateData(BaseModel):
    chat_session_id: uuid.UUID
    greeting: str
    suggestions: list[str]


class ChatMessageCreate(BaseModel):
    visitor_id: uuid.UUID
    content: str
    locale: str = "en"

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("content is required")
        if len(trimmed) > 500:
            raise ValueError("content must be 500 characters or fewer")
        return trimmed


class ChatMessageReplyData(BaseModel):
    reply: str
    sources: list[ChatSource]
    suggested_action: Literal["none", "rfq", "contact"] = "none"
    handoff_ready: bool = False
    handoff_prefill: dict[str, Any] = {}


class ChatHandoffCreate(BaseModel):
    visitor_id: uuid.UUID
    intent_reason: str
    prefill: dict[str, Any] = {}


class ChatHandoffData(BaseModel):
    rfq_prefill_url: str
    prefill: dict[str, Any]