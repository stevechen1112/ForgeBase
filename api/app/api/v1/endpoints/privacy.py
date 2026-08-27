"""Public analytics-consent lifecycle and server-side revocation."""
from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import resolve_tenant_id
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.consent_record import ConsentRecord
from app.models.visitor import Visitor
from app.services.privacy_operations import erase_anonymous_visitor

router = APIRouter(prefix="/privacy", tags=["Privacy"])


class ConsentDecisionIn(BaseModel):
    visitor_id: uuid.UUID
    status: Literal["granted", "denied", "revoked"]
    policy_version: str = Field(default=settings.CONSENT_POLICY_VERSION, max_length=40)
    source: str = Field(default="web", max_length=30)


def _visitor_hash(visitor_id: uuid.UUID, tenant_id: object | None) -> str:
    message = f"{tenant_id or 'public'}:{visitor_id}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


@router.post("/analytics-consent")
async def record_analytics_consent(
    body: ConsentDecisionIn,
    tenant_id: uuid.UUID | None = Depends(resolve_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    visitor = await db.get(Visitor, body.visitor_id)
    if visitor and visitor.tenant_id != tenant_id:
        raise HTTPException(status_code=422, detail="visitor_id does not belong to this site")

    db.add(ConsentRecord(
        tenant_id=tenant_id,
        visitor_hash=_visitor_hash(body.visitor_id, tenant_id),
        status=body.status,
        policy_version=body.policy_version,
        source=body.source,
    ))

    erased = {
        "deleted": {
            "tracking_events": 0,
            "tracking_sessions": 0,
            "network_observations": 0,
            "company_jobs": 0,
            "provider_usage": 0,
        },
        "preserved": [
            "rfq_requests",
            "chat_sessions",
            "contact_records",
            "rfq_business_records",
            "chat_business_records",
            "converted_contacts",
        ],
    }
    if body.status == "granted":
        if visitor is None:
            visitor = Visitor(visitor_id=body.visitor_id, tenant_id=tenant_id)
        visitor.analytics_consent_status = "granted"
        visitor.consent_updated_at = utcnow_naive()
        visitor.updated_at = utcnow_naive()
        db.add(visitor)
    else:
        if visitor is not None:
            erased = await erase_anonymous_visitor(
                db,
                tenant_id=tenant_id,
                visitor_id=body.visitor_id,
            ) or erased
            visitor.analytics_consent_status = body.status
            db.add(visitor)

    await db.commit()
    deleted = dict(erased["deleted"])
    deleted["events"] = deleted.pop("tracking_events", 0)
    deleted["sessions"] = deleted.pop("tracking_sessions", 0)
    return {
        "status": body.status,
        "policy_version": body.policy_version,
        "deleted": deleted,
        "preserved": erased["preserved"],
    }
