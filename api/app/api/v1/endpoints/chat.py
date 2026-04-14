import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import resolve_tenant_id
from app.db.session import get_session
from app.models.chat import ChatSession
from app.schemas.base import APIResponse
from app.schemas.chat import (
    ChatHandoffCreate,
    ChatHandoffData,
    ChatMessageCreate,
    ChatMessageReplyData,
    ChatSessionCreate,
    ChatSessionCreateData,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])


async def _get_chat_session_or_404(db: AsyncSession, chat_session_id: uuid.UUID) -> ChatSession:
    chat_session = await db.get(ChatSession, chat_session_id)
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_session


@router.post("/sessions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    body: ChatSessionCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    service = ChatService(db)
    chat_session, greeting, suggestions = await service.create_session(
        visitor_id=body.visitor_id,
        session_id=body.session_id,
        context_page=body.context_page,
        context_entity_type=body.context_entity_type,
        context_entity_id=body.context_entity_id,
        tenant_id=tenant_id,
    )
    return APIResponse(
        data=ChatSessionCreateData(
            chat_session_id=chat_session.id,
            greeting=greeting,
            suggestions=suggestions,
        )
    )


@router.post("/sessions/{chat_session_id}/messages", response_model=APIResponse)
async def create_chat_message(
    chat_session_id: uuid.UUID,
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_session),
):
    chat_session = await _get_chat_session_or_404(db, chat_session_id)
    if chat_session.visitor_id != body.visitor_id:
        raise HTTPException(status_code=403, detail="visitor_id does not match session owner")

    service = ChatService(db)
    result = await service.answer_message(chat_session=chat_session, content=body.content)
    return APIResponse(data=ChatMessageReplyData(**result))


@router.post("/sessions/{chat_session_id}/handoff", response_model=APIResponse)
async def create_chat_handoff(
    chat_session_id: uuid.UUID,
    body: ChatHandoffCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    chat_session = await _get_chat_session_or_404(db, chat_session_id)
    if chat_session.visitor_id != body.visitor_id:
        raise HTTPException(status_code=403, detail="visitor_id does not match session owner")

    service = ChatService(db)
    result = await service.create_handoff(chat_session=chat_session, prefill=body.prefill)

    # Copilot: notify human handoff
    if tenant_id:
        import asyncio
        from app.services.copilot import on_chat_handoff as _copilot_handoff
        asyncio.create_task(_copilot_handoff(chat_session_id, tenant_id))

    return APIResponse(data=ChatHandoffData(**result))