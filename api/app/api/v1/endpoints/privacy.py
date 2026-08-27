"""Public analytics-consent lifecycle and server-side revocation."""
from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.v1.deps import resolve_tenant_id
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.db.session import get_session
from app.models.consent_record import ConsentRecord
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.visitor import Visitor
from app.services.company_identification.privacy import delete_visitor_company_evidence

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

    deleted_events = 0
    deleted_sessions = 0
    deleted_company_evidence = {
        "network_observations": 0,
        "company_jobs": 0,
        "provider_usage": 0,
    }
    if body.status == "granted":
        if visitor is None:
            visitor = Visitor(visitor_id=body.visitor_id, tenant_id=tenant_id)
        visitor.analytics_consent_status = "granted"
        visitor.consent_updated_at = utcnow_naive()
        visitor.updated_at = utcnow_naive()
        db.add(visitor)
    else:
        if tenant_id is not None:
            deleted_company_evidence = await delete_visitor_company_evidence(
                db,
                tenant_id=tenant_id,
                visitor_id=body.visitor_id,
            )
        event_result = await db.exec(
            delete(TrackingEvent).where(
                TrackingEvent.visitor_id == body.visitor_id,
                TrackingEvent.tenant_id == tenant_id,
            )
        )
        session_result = await db.exec(
            delete(TrackingSession).where(
                TrackingSession.visitor_id == body.visitor_id,
                TrackingSession.tenant_id == tenant_id,
            )
        )
        deleted_events = int(event_result.rowcount or 0)
        deleted_sessions = int(session_result.rowcount or 0)
        if visitor:
            visitor.analytics_consent_status = body.status
            visitor.consent_updated_at = utcnow_naive()
            visitor.total_visits = 0
            visitor.total_page_views = 0
            visitor.intent_score = 0
            visitor.intent_stage = "cold"
            visitor.facet_product_interest = 0
            visitor.facet_trust_validation = 0
            visitor.facet_procurement_readiness = 0
            visitor.facet_urgency = 0
            visitor.intent_explanation = None
            visitor.ml_intent_score = None
            visitor.ml_score_updated_at = None
            visitor.stage_alert_sent = False
            visitor.device_type = None
            visitor.country = None
            visitor.updated_at = utcnow_naive()
            db.add(visitor)

    await db.commit()
    return {
        "status": body.status,
        "policy_version": body.policy_version,
        "deleted": {
            "events": deleted_events,
            "sessions": deleted_sessions,
            **deleted_company_evidence,
        },
        "preserved": ["rfq_requests", "chat_sessions", "contact_records"],
    }
