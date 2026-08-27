import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import resolve_tenant_id
from app.core.config import settings
from app.db.session import get_session
from app.models.chat import ChatSession
from app.models.rfq_draft import RFQDraft
from app.models.tenant import Tenant
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
from app.services.capability_access import tenant_has_feature

router = APIRouter(prefix="/chat", tags=["Chat"])


async def _get_chat_session_or_404(
    db: AsyncSession,
    chat_session_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> ChatSession:
    chat_session = await db.get(ChatSession, chat_session_id)
    if not chat_session or chat_session.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return chat_session


async def _ensure_chat_available(db: AsyncSession, tenant_id: Optional[uuid.UUID]) -> None:
    if not settings.CHAT_ENABLED:
        raise HTTPException(status_code=503, detail="AI advisor is temporarily unavailable")
    if tenant_id is None:
        if settings.is_production:
            raise HTTPException(status_code=503, detail="AI advisor tenant is not configured")
        return
    tenant = await db.get(Tenant, tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if not tenant_has_feature(tenant, "ai_advisor"):
        raise HTTPException(status_code=403, detail="AI advisor is not enabled for this tenant")


async def _resolve_chat_tenant_id(
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID],
) -> Optional[uuid.UUID]:
    """Apply the configured public tenant only to the AI advisor.

    The rest of the public content API must preserve its existing global
    (tenant_id IS NULL) catalog behavior.
    """
    if tenant_id is not None or not settings.PUBLIC_TENANT_SLUG:
        return tenant_id
    tenant = (
        await db.exec(
            select(Tenant).where(
                Tenant.slug == settings.PUBLIC_TENANT_SLUG,
                Tenant.is_active.is_(True),
            )
        )
    ).first()
    return tenant.id if tenant else None


@router.post("/sessions", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    body: ChatSessionCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    tenant_id = await _resolve_chat_tenant_id(db, tenant_id)
    await _ensure_chat_available(db, tenant_id)
    service = ChatService(db)
    chat_session, greeting, suggestions = await service.create_session(
        visitor_id=body.visitor_id,
        session_id=body.session_id,
        context_page=body.context_page,
        context_entity_type=body.context_entity_type,
        context_entity_id=body.context_entity_id,
        tenant_id=tenant_id,
        locale=body.locale,
    )
    return APIResponse(
        data=ChatSessionCreateData(
            chat_session_id=chat_session.id,
            greeting=greeting,
            suggestions=suggestions,
            response_locale=chat_session.locale,
        )
    )


@router.post("/sessions/{chat_session_id}/messages", response_model=APIResponse)
async def create_chat_message(
    chat_session_id: uuid.UUID,
    body: ChatMessageCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    tenant_id = await _resolve_chat_tenant_id(db, tenant_id)
    chat_session = await _get_chat_session_or_404(db, chat_session_id, tenant_id)
    await _ensure_chat_available(db, tenant_id)
    if chat_session.visitor_id != body.visitor_id:
        raise HTTPException(status_code=403, detail="visitor_id does not match session owner")

    service = ChatService(db)
    result = await service.answer_message(
        chat_session=chat_session,
        content=body.content,
        locale=body.locale,
    )
    return APIResponse(data=ChatMessageReplyData(**result))


@router.post("/sessions/{chat_session_id}/handoff", response_model=APIResponse)
async def create_chat_handoff(
    chat_session_id: uuid.UUID,
    body: ChatHandoffCreate,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    tenant_id = await _resolve_chat_tenant_id(db, tenant_id)
    chat_session = await _get_chat_session_or_404(db, chat_session_id, tenant_id)
    await _ensure_chat_available(db, tenant_id)
    if chat_session.visitor_id != body.visitor_id:
        raise HTTPException(status_code=403, detail="visitor_id does not match session owner")

    service = ChatService(db)
    result = await service.create_handoff(
        chat_session=chat_session,
        prefill=body.prefill.model_dump(mode="json", exclude_none=True),
    )

    return APIResponse(data=ChatHandoffData(**result))


@router.get("/handoffs/{draft_id}", response_model=APIResponse)
async def get_chat_handoff_draft(
    draft_id: uuid.UUID,
    visitor_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    tenant_id: Optional[uuid.UUID] = Depends(resolve_tenant_id),
):
    """Return an unexpired handoff only to the browser visitor that created it."""
    from app.core.datetime import utcnow_naive

    tenant_id = await _resolve_chat_tenant_id(db, tenant_id)
    draft = (
        await db.exec(
            select(RFQDraft).where(
                RFQDraft.id == draft_id,
                RFQDraft.visitor_id == visitor_id,
                RFQDraft.tenant_id == tenant_id,
                RFQDraft.consumed_at.is_(None),
                RFQDraft.expires_at > utcnow_naive(),
            )
        )
    ).first()
    if not draft:
        raise HTTPException(status_code=404, detail="RFQ handoff draft not found or expired")
    return APIResponse(
        data={
            "draft_id": str(draft.id),
            "chat_session_id": str(draft.chat_session_id),
            "expires_at": draft.expires_at.isoformat(),
            "prefill": json.loads(draft.payload_json),
        }
    )
