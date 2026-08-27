"""Auditable privacy exports, erasure, and retention inventory."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, text
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.models.chat import ChatMessage, ChatSession
from app.models.company_identification import CompanyIdentification, NetworkObservation
from app.models.contact_enrichment import ContactCandidate
from app.models.inbound_reply import InboundReply
from app.models.outreach import JourneySnapshot, OutreachMessage
from app.models.rfq_request import RFQRequest
from app.models.tracking_event import TrackingEvent
from app.models.tracking_session import TrackingSession
from app.models.visitor import Visitor
from app.services.company_identification.privacy import delete_visitor_company_evidence


def privacy_request_fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(
        b"forgebase-privacy-operation-v1\0" + canonical.encode("utf-8")
    ).hexdigest()


def privacy_subject_hash(*, tenant_id: uuid.UUID, visitor_id: uuid.UUID) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        f"privacy-subject:{tenant_id}:{visitor_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def _count(db: AsyncSession, model: Any, *where: Any) -> int:
    return int((await db.exec(select(func.count()).select_from(model).where(*where))).one())


async def retention_inventory(db: AsyncSession) -> dict[str, Any]:
    now = utcnow_naive()
    analytics_cutoff = now - timedelta(days=max(1, settings.ANALYTICS_RETENTION_DAYS))
    expired_observation_ids = set(
        (
            await db.exec(
                select(NetworkObservation.id).where(NetworkObservation.expires_at <= now)
            )
        ).all()
    )
    protected_observation_ids: set[uuid.UUID] = set()
    if expired_observation_ids:
        protected_observation_ids.update(
            (
                await db.exec(
                    select(CompanyIdentification.network_observation_id)
                    .join(
                        ContactCandidate,
                        ContactCandidate.company_identification_id
                        == CompanyIdentification.id,
                    )
                    .where(
                        col(CompanyIdentification.network_observation_id).in_(
                            expired_observation_ids
                        ),
                        ContactCandidate.status == "converted",
                    )
                )
            ).all()
        )
        protected_observation_ids.update(
            (
                await db.exec(
                    select(CompanyIdentification.network_observation_id)
                    .join(
                        OutreachMessage,
                        OutreachMessage.company_identification_id
                        == CompanyIdentification.id,
                    )
                    .where(
                        col(CompanyIdentification.network_observation_id).in_(
                            expired_observation_ids
                        )
                    )
                )
            ).all()
        )
    counts = {
        "tracking_events": await _count(db, TrackingEvent, TrackingEvent.timestamp < analytics_cutoff),
        "tracking_sessions": await _count(db, TrackingSession, TrackingSession.updated_at < analytics_cutoff),
        "network_observations": len(expired_observation_ids - protected_observation_ids),
        "contact_candidates": await _count(
            db,
            ContactCandidate,
            ContactCandidate.expires_at <= now,
            ContactCandidate.status != "converted",
            ~select(OutreachMessage.id)
            .where(OutreachMessage.contact_candidate_id == ContactCandidate.id)
            .exists(),
        ),
        "journey_snapshots": await _count(
            db,
            JourneySnapshot,
            JourneySnapshot.expires_at <= now,
            ~select(OutreachMessage.id)
            .where(OutreachMessage.journey_snapshot_id == JourneySnapshot.id)
            .exists(),
        ),
        "inbound_reply_contents": await _count(
            db,
            InboundReply,
            InboundReply.expires_at <= now,
            InboundReply.content_redacted_at.is_(None),
        ),
    }
    expired_contact_total = await _count(
        db, ContactCandidate, ContactCandidate.expires_at <= now
    )
    expired_snapshot_total = await _count(
        db, JourneySnapshot, JourneySnapshot.expires_at <= now
    )
    return {
        "generated_at": now,
        "analytics_retention_days": max(1, settings.ANALYTICS_RETENTION_DAYS),
        "analytics_cutoff": analytics_cutoff,
        "expired": counts,
        "total_expired": sum(counts.values()),
        "retained_business_evidence": {
            "network_observations": len(protected_observation_ids),
            "contact_candidates": max(
                0, expired_contact_total - counts["contact_candidates"]
            ),
            "journey_snapshots": max(
                0, expired_snapshot_total - counts["journey_snapshots"]
            ),
        },
        "policy": {
            "tracking": "delete",
            "company_evidence": "delete",
            "unconverted_contact_candidates": "delete",
            "journey_snapshots": "delete",
            "inbound_reply_content": "redact_content_keep_audit",
            "converted_contacts_and_rfqs": "preserve_business_record",
        },
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _json_value(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


async def export_anonymous_visitor(
    db: AsyncSession, *, tenant_id: uuid.UUID, visitor_id: uuid.UUID
) -> dict[str, Any] | None:
    visitor = await db.get(Visitor, visitor_id)
    if not visitor or visitor.tenant_id != tenant_id:
        return None
    events = list(
        (
            await db.exec(
                select(TrackingEvent)
                .where(
                    TrackingEvent.tenant_id == tenant_id,
                    TrackingEvent.visitor_id == visitor_id,
                )
                .order_by(TrackingEvent.timestamp)
            )
        ).all()
    )
    sessions = list(
        (
            await db.exec(
                select(TrackingSession)
                .where(
                    TrackingSession.tenant_id == tenant_id,
                    TrackingSession.visitor_id == visitor_id,
                )
                .order_by(TrackingSession.start_time)
            )
        ).all()
    )
    companies = list(
        (
            await db.exec(
                select(CompanyIdentification).where(
                    CompanyIdentification.tenant_id == tenant_id,
                    CompanyIdentification.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    company_ids = [row.id for row in companies]
    candidates = (
        list(
            (
                await db.exec(
                    select(ContactCandidate).where(
                        ContactCandidate.tenant_id == tenant_id,
                        ContactCandidate.company_identification_id.in_(company_ids),
                    )
                )
            ).all()
        )
        if company_ids
        else []
    )
    snapshots = list(
        (
            await db.exec(
                select(JourneySnapshot).where(
                    JourneySnapshot.tenant_id == tenant_id,
                    JourneySnapshot.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    messages = list(
        (
            await db.exec(
                select(OutreachMessage).where(
                    OutreachMessage.tenant_id == tenant_id,
                    OutreachMessage.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    chats = list(
        (
            await db.exec(
                select(ChatSession).where(
                    ChatSession.tenant_id == tenant_id,
                    ChatSession.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    chat_ids = [row.id for row in chats]
    chat_messages = (
        list(
            (
                await db.exec(
                    select(ChatMessage)
                    .where(ChatMessage.chat_session_id.in_(chat_ids))
                    .order_by(ChatMessage.created_at)
                )
            ).all()
        )
        if chat_ids
        else []
    )
    rfqs = list(
        (
            await db.exec(
                select(RFQRequest).where(
                    RFQRequest.tenant_id == tenant_id,
                    RFQRequest.visitor_id == visitor_id,
                )
            )
        ).all()
    )
    return {
        "schema_version": 1,
        "exported_at": utcnow_naive(),
        "tenant_id": str(tenant_id),
        "visitor": {
            "visitor_id": str(visitor.visitor_id),
            "first_seen": _iso(visitor.first_seen),
            "last_seen": _iso(visitor.last_seen),
            "consent_status": visitor.analytics_consent_status,
            "consent_updated_at": _iso(visitor.consent_updated_at),
            "intent_score": visitor.intent_score,
            "intent_stage": visitor.intent_stage,
            "country": visitor.country,
            "device_type": visitor.device_type,
            "linked_to_known_contact": visitor.contact_id is not None,
        },
        "sessions": [
            {
                "session_id": str(row.session_id),
                "start_time": _iso(row.start_time),
                "end_time": _iso(row.end_time),
                "page_count": row.page_count,
                "entry_page": row.entry_page,
                "exit_page": row.exit_page,
                "traffic_source": row.traffic_source,
                "country": row.country,
                "device_type": row.device_type,
            }
            for row in sessions
        ],
        "events": [
            {
                "event_id": str(row.event_id),
                "event_name": row.event_name,
                "timestamp": _iso(row.timestamp),
                "page_url": row.page_url,
                "page_type": row.page_type,
                "locale": row.locale,
                "traffic_source": row.traffic_source,
                "score_delta": row.score_delta,
            }
            for row in events
        ],
        "company_candidates": [
            {
                "id": str(row.id),
                "company_name": row.company_name,
                "domain": row.domain,
                "provider": row.provider,
                "confidence": row.confidence,
                "status": row.status,
                "created_at": _iso(row.created_at),
                "expires_at": _iso(row.expires_at),
            }
            for row in companies
        ],
        "company_contact_candidates": [
            {
                "id": str(row.id),
                "full_name": row.full_name,
                "job_title": row.job_title,
                "email_masked": row.email_masked,
                "status": row.status,
                "source_provider": row.source_provider,
                "expires_at": _iso(row.expires_at),
            }
            for row in candidates
        ],
        "journey_snapshots": [
            {
                "id": str(row.id),
                "intent_score": row.intent_score,
                "intent_stage": row.intent_stage,
                "summary": row.summary,
                "generated_at": _iso(row.generated_at),
                "expires_at": _iso(row.expires_at),
            }
            for row in snapshots
        ],
        "outreach_messages": [
            {
                "id": str(row.id),
                "recipient": row.to_email_masked,
                "status": row.status,
                "subject": row.sent_subject_snapshot or row.subject_snapshot,
                "created_at": _iso(row.created_at),
                "sent_at": _iso(row.sent_at),
            }
            for row in messages
        ],
        "chat_sessions": [
            {
                "id": str(row.id),
                "locale": row.locale,
                "status": row.status,
                "started_at": _iso(row.started_at),
                "ended_at": _iso(row.ended_at),
            }
            for row in chats
        ],
        "chat_messages": [
            {
                "id": str(row.id),
                "chat_session_id": str(row.chat_session_id),
                "role": row.role,
                "content": row.content,
                "created_at": _iso(row.created_at),
            }
            for row in chat_messages
        ],
        "rfqs": [
            {
                "id": str(row.id),
                "rfq_number": row.rfq_number,
                "status": row.status,
                "form_data": _json_value(row.form_data),
                "created_at": _iso(row.created_at),
            }
            for row in rfqs
        ],
        "excluded_security_fields": [
            "raw_ip",
            "provider_raw_payload",
            "encryption_ciphertext",
            "token_hashes",
        ],
    }


async def erase_anonymous_visitor(
    db: AsyncSession, *, tenant_id: uuid.UUID | None, visitor_id: uuid.UUID
) -> dict[str, Any] | None:
    visitor = await db.get(Visitor, visitor_id)
    if not visitor or visitor.tenant_id != tenant_id:
        return None
    deleted_company = (
        await delete_visitor_company_evidence(
            db, tenant_id=tenant_id, visitor_id=visitor_id
        )
        if tenant_id is not None
        else {"network_observations": 0, "company_jobs": 0, "provider_usage": 0}
    )
    events = await db.exec(
        delete(TrackingEvent).where(
            TrackingEvent.tenant_id == tenant_id,
            TrackingEvent.visitor_id == visitor_id,
        )
    )
    sessions = await db.exec(
        delete(TrackingSession).where(
            TrackingSession.tenant_id == tenant_id,
            TrackingSession.visitor_id == visitor_id,
        )
    )
    visitor.analytics_consent_status = "revoked"
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
    return {
        "deleted": {
            "tracking_events": int(events.rowcount or 0),
            "tracking_sessions": int(sessions.rowcount or 0),
            **deleted_company,
        },
        "anonymized": ["visitor_profile"],
        "preserved": [
            "consent_decision_hash",
            "rfq_requests",
            "chat_sessions",
            "contact_records",
            "rfq_business_records",
            "chat_business_records",
            "converted_contacts",
            "sent_message_delivery_audit",
        ],
    }


async def run_scheduled_retention(db: AsyncSession) -> dict[str, Any]:
    """Run the daily retention transaction once across scheduler replicas."""
    from app.models.privacy_operation import PrivacyOperation
    from app.services.privacy_retention import purge_expired_analytics

    day = utcnow_naive().date().isoformat()
    key = f"scheduled-retention:{day}"
    fingerprint = privacy_request_fingerprint(
        {"operation_type": "retention_run", "schedule_day": day}
    )
    if db.get_bind().dialect.name == "postgresql":
        await db.exec(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            params={"lock_key": "forgebase-privacy:scheduled-retention"},
        )
    replay = (
        await db.exec(
            select(PrivacyOperation).where(PrivacyOperation.idempotency_key == key)
        )
    ).first()
    if replay:
        return {**json.loads(replay.result_json), "replayed": True}
    before = await retention_inventory(db)
    processed = await purge_expired_analytics(db, commit=False)
    after = await retention_inventory(db)
    run = PrivacyOperation(
        idempotency_key=key,
        request_fingerprint=fingerprint,
        operation_type="retention_run",
        reason="Daily automated retention policy",
        result_json="{}",
    )
    result = {
        "operation_id": str(run.id),
        "operation_type": "retention_run",
        "before": before["expired"],
        "processed": processed,
        "after": after["expired"],
        "replayed": False,
    }
    run.result_json = json.dumps(result, default=str)
    db.add(run)
    await db.commit()
    return result
