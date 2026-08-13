import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


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
    needs_clarification: bool = False
    clarifying_question: Optional[str] = None
    handoff_ready: bool = False
    handoff_prefill: dict[str, Any] = Field(default_factory=dict)
    ai_available: bool = True


class ChatHandoffPrefill(BaseModel):
    product_ids: list[uuid.UUID] = Field(default_factory=list, max_length=10)
    application_id: Optional[uuid.UUID] = None
    quantity: Optional[str] = Field(default=None, max_length=100)
    specifications: Optional[str] = Field(default=None, max_length=2000)
    message: Optional[str] = Field(default=None, max_length=2000)
    requirement_summary: Optional[str] = Field(default=None, max_length=2000)


class ChatHandoffCreate(BaseModel):
    visitor_id: uuid.UUID
    intent_reason: str = Field(max_length=100)
    prefill: ChatHandoffPrefill = Field(default_factory=ChatHandoffPrefill)


class ChatHandoffData(BaseModel):
    rfq_prefill_url: str
    prefill: dict[str, Any]


class GeneratedChatPayload(BaseModel):
    reply: str = Field(min_length=1, max_length=3000)
    needs_clarification: bool = False
    clarifying_question: Optional[str] = Field(default=None, max_length=500)
    suggested_action: Literal["none", "rfq", "contact"] = "none"
    handoff_reason: Optional[str] = Field(default=None, max_length=500)
    prefill: dict[str, Any] = Field(default_factory=dict)
    ai_available: bool = True
