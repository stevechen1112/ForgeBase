"""Notification preferences and history for the operating dashboard."""
from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field as PydanticField
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import RequireFeature, get_current_user
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.notification_log import NotificationLog
from app.models.notification_preference import NotificationPreference
from app.models.tenant import Tenant
from app.models.user import User
from app.services.capability_access import tenant_has_feature
from app.services.notification_channel_policy import ACTIVE_NOTIFICATION_CHANNELS

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class PreferenceIn(BaseModel):
    channel: str
    channel_config: dict = PydanticField(default_factory=dict)
    enabled: bool = True
    notify_new_rfq: bool = True
    notify_daily_summary: bool = True
    notify_chat_handoff: bool = True
    notify_content_suggestion: bool = False
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


class PreferenceUpdate(BaseModel):
    enabled: Optional[bool] = None
    notify_new_rfq: Optional[bool] = None
    notify_daily_summary: Optional[bool] = None
    notify_chat_handoff: Optional[bool] = None
    notify_content_suggestion: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None


async def _preference(pref_id: uuid.UUID, db: AsyncSession, user: User) -> NotificationPreference:
    pref = await db.get(NotificationPreference, pref_id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    if pref.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return pref


def _preference_payload(pref: NotificationPreference) -> dict:
    return {
        "id": str(pref.id),
        "channel": pref.channel,
        "channel_config": json.loads(pref.channel_config or "{}"),
        "enabled": pref.enabled,
        "notify_new_rfq": pref.notify_new_rfq,
        "notify_daily_summary": pref.notify_daily_summary,
        "notify_chat_handoff": pref.notify_chat_handoff,
        "notify_content_suggestion": pref.notify_content_suggestion,
        "quiet_hours_start": pref.quiet_hours_start,
        "quiet_hours_end": pref.quiet_hours_end,
        "created_at": pref.created_at.isoformat(),
    }


@router.get("/preferences", dependencies=[Depends(RequireFeature("notifications"))])
async def list_preferences(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await db.exec(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == current_user.id)
        .order_by(NotificationPreference.created_at)
    )
    return {"data": [_preference_payload(pref) for pref in result.all()]}


@router.post(
    "/preferences",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RequireFeature("notifications"))],
)
async def create_preference(
    body: PreferenceIn,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    channel = body.channel.strip().lower()
    if channel not in ACTIVE_NOTIFICATION_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel. Allowed: {ACTIVE_NOTIFICATION_CHANNELS}",
        )
    pref = NotificationPreference(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        channel=channel,
        channel_config=json.dumps(body.channel_config),
        **body.model_dump(exclude={"channel", "channel_config"}),
    )
    db.add(pref)
    await db.commit()
    await db.refresh(pref)
    return {"data": {"id": str(pref.id)}}


@router.put("/preferences/{pref_id}", dependencies=[Depends(RequireFeature("notifications"))])
async def update_preference(
    pref_id: uuid.UUID,
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pref = await _preference(pref_id, db, current_user)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(pref, field, value)
    pref.updated_at = utcnow_naive()
    db.add(pref)
    await db.commit()
    return {"ok": True}


@router.delete(
    "/preferences/{pref_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RequireFeature("notifications"))],
)
async def delete_preference(
    pref_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pref = await _preference(pref_id, db, current_user)
    await db.delete(pref)
    await db.commit()


@router.get("/history", dependencies=[Depends(RequireFeature("notifications"))])
async def list_notifications(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    allowed_event_types = {"new_rfq", "daily_summary"}
    if tenant and tenant_has_feature(tenant, "chat_handoff"):
        allowed_event_types.add("chat_handoff")
    if tenant and tenant_has_feature(tenant, "full_tracking"):
        allowed_event_types.add("content_suggestion")
    result = await db.exec(
        select(NotificationLog)
        .where(NotificationLog.tenant_id == current_user.tenant_id)
        .where(NotificationLog.event_type.in_(allowed_event_types))
        .order_by(NotificationLog.sent_at.desc())
        .limit(100)
    )
    return {
        "data": [
            {
                "id": str(log.id),
                "channel": log.channel,
                "event_type": log.event_type,
                "event_ref_id": str(log.event_ref_id) if log.event_ref_id else None,
                "message_preview": log.message_preview,
                "status": log.status,
                "sent_at": log.sent_at.isoformat(),
            }
            for log in result.all()
        ]
    }
