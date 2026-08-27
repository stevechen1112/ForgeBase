"""Hermetic North Star lab: anonymous visit through won RFQ attribution.

This is intentionally one end-to-end test rather than another collection of
component assertions.  Every external lookup and email call is replaced by a
deterministic in-process fake; PostgreSQL and the real application services,
API routes, policies, audit records, signatures and tenant filters remain in
the path.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from app.api.v1.endpoints.company_identification import (
    IdentificationReviewIn,
    review_company_candidate,
)
from app.api.v1.endpoints.contact_enrichment import (
    CandidateDecisionIn,
    review_candidate,
)
from app.api.v1.endpoints.outreach import (
    DeliveryActionIn,
    DraftDecisionIn,
    queue_message_send,
    review_message,
)
from app.api.v1.endpoints.webhooks import receive_resend_webhook
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt
from app.models.company_identification import (
    CompanyIdentification,
    GrowthAutomationPolicy,
    NetworkObservation,
)
from app.models.contact_enrichment import ContactCandidate, ContactPersonaPolicy
from app.models.email_delivery import EmailDeliveryEvent
from app.models.inbound_reply import InboundReply, InboundReplyPolicy, SalesHandoff
from app.models.operational_job import OperationalJob
from app.models.outreach import (
    JourneySnapshot,
    OutreachDeliveryPolicy,
    OutreachDraftPolicy,
    OutreachMessage,
)
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.rfq_request import RFQRequest
from app.models.tracking_event import TrackingEvent
from app.models.user import User
from app.models.visitor import Visitor
from app.services.company_identification.eligibility import (
    maybe_create_network_observation,
)
from app.services.company_identification.providers.base import CompanyCandidate
from app.services.company_identification.providers.mock import (
    MockCompanyIdentificationProvider,
)
from app.services.company_identification.runtime import (
    run_company_identification_job,
)
from app.services.contact_enrichment.runtime import run_contact_enrichment_job
from app.services.email_service import EmailDeliveryResult
from app.services.inbound_reply.runtime import (
    ingest_resend_receipt,
    run_inbound_reply_fetch,
)
from app.services.intent_facets import apply_event_to_visitor
from app.services.intent_scoring import calculate_score_delta, get_intent_stage
from app.services.outreach.delivery import run_outreach_send_job
from app.services.outreach.runtime import (
    run_journey_summarize_job,
    run_outreach_draft_job,
)
from sqlmodel import func, select
from starlette.requests import Request

from tests.conftest import _make_engine, requires_db


def _session_context(factory):
    @asynccontextmanager
    async def context():
        async with factory() as session:
            yield session

    return context


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _request(raw: bytes, event_id: str, timestamp: str, signature: str) -> Request:
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": raw, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/webhooks/resend",
            "headers": [
                (b"svix-id", event_id.encode()),
                (b"svix-timestamp", timestamp.encode()),
                (b"svix-signature", f"v1,{signature}".encode()),
            ],
        },
        receive,
    )


def _write_success_report(milestones: list[dict[str, object]]) -> None:
    target = os.getenv("FORGEBASE_NORTH_STAR_REPORT", "").strip()
    if not target:
        return
    path = Path(target).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "lab": "north-star-full-e2e",
                "status": "passed",
                "external_network_calls": 0,
                "finished_at": utcnow_naive().isoformat() + "Z",
                "milestones": milestones,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


@requires_db
@pytest.mark.asyncio
async def test_north_star_full_chain_isolated_idempotent_and_attributed(
    two_tenants,
    admin_token_for_tenant,
    http_client,
    monkeypatch,
) -> None:
    tenant, other = two_tenants
    engine, factory = _make_engine()
    session_context = _session_context(factory)
    monkeypatch.setattr(
        "app.services.company_identification.runtime.get_session_ctx",
        session_context,
    )
    monkeypatch.setattr(
        "app.services.contact_enrichment.runtime.get_session_ctx", session_context
    )
    monkeypatch.setattr(
        "app.services.outreach.runtime.get_session_ctx", session_context
    )
    monkeypatch.setattr(
        "app.services.outreach.delivery.get_session_ctx", session_context
    )
    monkeypatch.setattr(
        "app.services.inbound_reply.runtime.get_session_ctx", session_context
    )

    domain = f"north-star-{uuid.uuid4().hex[:10]}.example"
    provider = MockCompanyIdentificationProvider(
        {
            "8.8.8.8": (
                CompanyCandidate(
                    company_name="North Star Buyer Co",
                    candidate_key=domain,
                    confidence=0.96,
                    match_method="mock_business_network",
                    domain=domain,
                    evidence={"signals": ["asn", "company_domain"]},
                ),
            )
        }
    )
    monkeypatch.setattr(
        "app.services.company_identification.runtime.get_company_identification_provider",
        lambda _: provider,
    )

    webhook_key = b"n" * 32
    monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", True)
    monkeypatch.setattr(settings, "OUTREACH_SEND_ENABLED", True)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "north-star-lab-key")
    monkeypatch.setattr(
        settings,
        "RESEND_WEBHOOK_SECRET",
        "whsec_" + base64.b64encode(webhook_key).decode(),
    )
    monkeypatch.setattr(
        settings, "OUTREACH_PUBLIC_BASE_URL", "https://api.north-star.test"
    )
    monkeypatch.setattr(
        settings, "OUTREACH_UNSUBSCRIBE_SECRET", "north-star-unsubscribe-" + "u" * 40
    )
    monkeypatch.setattr(settings, "INBOUND_REPLY_ENABLED", True)
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_DOMAIN", "reply.north-star.test")
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_SECRET", "r" * 40)

    provider_deliveries: list[dict[str, object]] = []

    async def fake_send(**kwargs):
        provider_deliveries.append(kwargs)
        return EmailDeliveryResult(
            True,
            True,
            False,
            "resend",
            message_id="resend-north-star-lab",
        )

    monkeypatch.setattr("app.services.outreach.delivery.send_email_result", fake_send)

    milestones: list[dict[str, object]] = []
    try:
        now = utcnow_naive()
        visitor_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        product_id: uuid.UUID
        async with factory() as db:
            tenant.feature_overrides = {
                **(tenant.feature_overrides or {}),
                "outreach_send": True,
                "inbound_reply": True,
                "sales_handoff": True,
                "closed_loop_attribution": True,
            }
            other.feature_overrides = {
                **(other.feature_overrides or {}),
                "inbound_reply": True,
                "sales_handoff": True,
                "closed_loop_attribution": True,
            }
            db.add(tenant)
            db.add(other)
            db.add(
                User(
                    id=actor_id,
                    tenant_id=tenant.id,
                    email=f"north-star-reviewer-{uuid.uuid4().hex[:8]}@test.invalid",
                    hashed_password="test-only",
                    full_name="North Star Reviewer",
                    role="admin",
                    is_superuser=True,
                )
            )
            db.add(
                GrowthAutomationPolicy(
                    tenant_id=tenant.id,
                    company_identification_mode="shadow",
                    provider_name="mock",
                    min_intent_score=40,
                    daily_provider_cost_limit=Decimal(10),
                )
            )
            db.add(
                ContactPersonaPolicy(
                    tenant_id=tenant.id,
                    mode="review_only",
                    contact_provider_name="mock",
                    verification_provider_name="mock",
                    target_departments=["procurement", "engineering"],
                    target_titles=["procurement", "engineering"],
                    target_seniorities=["manager", "director"],
                    min_relevance_score=60,
                )
            )
            db.add(
                OutreachDraftPolicy(
                    tenant_id=tenant.id,
                    mode="review_only",
                    allowed_languages=["en"],
                    lookback_days=30,
                    snapshot_retention_days=30,
                )
            )
            db.add(
                OutreachDeliveryPolicy(
                    tenant_id=tenant.id,
                    mode="approval_send",
                    quiet_hours_enabled=False,
                    daily_send_quota=10,
                )
            )
            db.add(
                InboundReplyPolicy(
                    tenant_id=tenant.id,
                    mode="review_only",
                    handoff_sla_hours=4,
                )
            )

            visitor = Visitor(
                visitor_id=visitor_id,
                tenant_id=tenant.id,
                analytics_consent_status="granted",
            )
            db.add(visitor)
            category = ProductCategory(
                tenant_id=tenant.id,
                category_name="Industrial Pumps",
                slug=f"industrial-pumps-{uuid.uuid4().hex[:8]}",
                status="published",
                locale="en",
            )
            db.add(category)
            await db.flush()
            product = Product(
                tenant_id=tenant.id,
                product_name="NX-500 Industrial Pump",
                slug=f"nx-500-{uuid.uuid4().hex[:8]}",
                model_number=f"NX-{uuid.uuid4().hex[:8]}",
                short_description="Published industrial pump information.",
                category_id=category.id,
                status="published",
                locale="en",
                published_at=now,
            )
            db.add(product)
            await db.flush()
            product_id = product.id

            event_names = [
                "product_view",
                "product_view",
                "spec_download",
                "comparison_view",
                "return_visit",
                "rfq_start",
            ]
            score = 0
            for index, event_name in enumerate(event_names):
                properties = {
                    "repeat_view": index == 1,
                    "days_since_last": 1,
                }
                delta = calculate_score_delta(event_name, properties)
                score += delta
                apply_event_to_visitor(visitor, event_name, delta, "product")
                db.add(
                    TrackingEvent(
                        tenant_id=tenant.id,
                        visitor_id=visitor_id,
                        event_name=event_name,
                        score_delta=delta,
                        timestamp=now + timedelta(milliseconds=index),
                        page_type="product",
                        page_id=product.id,
                        locale="en",
                        country="TW",
                        ip_address="8.8.8.8" if index == 0 else None,
                    )
                )
            visitor.intent_score = score
            visitor.intent_stage = get_intent_stage(score)
            db.add(visitor)
            await db.flush()
            source_event = (
                await db.exec(
                    select(TrackingEvent).where(
                        TrackingEvent.tenant_id == tenant.id,
                        TrackingEvent.visitor_id == visitor_id,
                        TrackingEvent.ip_address == "8.8.8.8",
                    )
                )
            ).one()
            observation = await maybe_create_network_observation(
                db,
                tenant_id=tenant.id,
                visitor=visitor,
                source_event=source_event,
                client_ip="8.8.8.8",
                analytics_consent=True,
                user_agent="Mozilla/5.0 NorthStarLab",
            )
            assert observation is not None
            observation_id = observation.id
            await db.commit()
        assert score >= 40 and get_intent_stage(score) in {"hot", "sales_ready"}
        milestones.append({"stage": "anonymous_behavior_intent", "intent_score": score})

        await run_company_identification_job(observation_id)
        await run_company_identification_job(observation_id)
        async with factory() as db:
            companies = (
                await db.exec(
                    select(CompanyIdentification).where(
                        CompanyIdentification.tenant_id == tenant.id,
                        CompanyIdentification.network_observation_id == observation_id,
                    )
                )
            ).all()
            assert len(companies) == 1
            company = companies[0]
            actor = await db.get(User, actor_id)
            assert actor is not None
            await review_company_candidate(
                company.id,
                IdentificationReviewIn(decision="confirm", note="North Star lab"),
                db,
                actor,
            )
            company_id = company.id
        milestones.append(
            {"stage": "company_confirmed", "company_identification_id": str(company_id)}
        )

        assert await run_contact_enrichment_job(company_id) == 2
        assert await run_contact_enrichment_job(company_id) == 0
        async with factory() as db:
            candidates = (
                await db.exec(
                    select(ContactCandidate)
                    .where(
                        ContactCandidate.tenant_id == tenant.id,
                        ContactCandidate.company_identification_id == company_id,
                    )
                    .order_by(ContactCandidate.full_name)
                )
            ).all()
            assert len(candidates) == 2
            candidate = next(
                row for row in candidates if row.department == "procurement"
            )
            actor = await db.get(User, actor_id)
            assert actor is not None
            await review_candidate(
                candidate.id,
                CandidateDecisionIn(decision="approve", note="Persona matched"),
                db,
                actor,
            )
            candidate_id = candidate.id
            recipient = decrypt(candidate.email_ciphertext)
        milestones.append(
            {"stage": "contact_approved", "contact_candidate_id": str(candidate_id)}
        )

        snapshot_id = await run_journey_summarize_job(candidate_id)
        assert await run_journey_summarize_job(candidate_id) == snapshot_id
        message_id = await run_outreach_draft_job(snapshot_id, candidate_id)
        assert await run_outreach_draft_job(snapshot_id, candidate_id) == message_id
        async with factory() as db:
            snapshot = await db.get(JourneySnapshot, snapshot_id)
            message = await db.get(OutreachMessage, message_id)
            actor = await db.get(User, actor_id)
            assert snapshot is not None and message is not None and actor is not None
            assert snapshot.top_products[0]["id"] == str(product_id)
            assert "NX-500 Industrial Pump" in message.subject_snapshot
            await review_message(
                message.id,
                DraftDecisionIn(decision="approve", note="Evidence checked"),
                db,
                actor,
            )
            queued = await queue_message_send(
                message.id,
                DeliveryActionIn(note="Approved lab delivery"),
                db,
                actor,
            )
            assert queued["message"]["status"] == "queued"
            duplicate_queue = await queue_message_send(
                message.id, DeliveryActionIn(), db, actor
            )
            assert duplicate_queue["duplicate"] is True
        milestones.append(
            {
                "stage": "journey_personalized_message_approved",
                "journey_snapshot_id": str(snapshot_id),
                "outreach_message_id": str(message_id),
            }
        )

        await run_outreach_send_job(message_id)
        await run_outreach_send_job(message_id)
        assert len(provider_deliveries) == 1
        assert provider_deliveries[0]["to"] == recipient
        assert provider_deliveries[0]["reply_to"].endswith("@reply.north-star.test")

        event_id = f"north-star-delivery-{uuid.uuid4()}"
        timestamp = str(int(time.time()))
        raw = json.dumps(
            {
                "type": "email.delivered",
                "created_at": utcnow_naive().isoformat() + "Z",
                "data": {
                    "email_id": "resend-north-star-lab",
                    "to": [recipient],
                },
            }
        ).encode()
        signed = f"{event_id}.{timestamp}.".encode() + raw
        signature = base64.b64encode(
            hmac.new(webhook_key, signed, hashlib.sha256).digest()
        ).decode()
        async with factory() as db:
            first_webhook = await receive_resend_webhook(
                _request(raw, event_id, timestamp, signature), db
            )
            duplicate_webhook = await receive_resend_webhook(
                _request(raw, event_id, timestamp, signature), db
            )
            assert first_webhook["duplicate"] is False
            assert duplicate_webhook["duplicate"] is True
            delivery_events = (
                await db.exec(
                    select(EmailDeliveryEvent).where(
                        EmailDeliveryEvent.provider_event_id == event_id
                    )
                )
            ).all()
            assert len(delivery_events) == 1
            message = await db.get(OutreachMessage, message_id)
            assert message is not None and message.status == "delivered"
            reply_to = message.sent_reply_to
            assert reply_to
        milestones.append({"stage": "delivery_confirmed", "provider_events": 1})

        async def fake_fetch(provider_email_id: str) -> dict:
            assert provider_email_id == "received-north-star-lab"
            return {
                "id": provider_email_id,
                "from": f"Procurement Contact <{recipient}>",
                "to": [reply_to],
                "subject": "Re: NX-500 Industrial Pump",
                "text": "Please quote 500 units and advise lead time.",
                "headers": {},
                "message_id": "<buyer-north-star-reply@example.test>",
                "attachments": [],
            }

        async def fake_notification(*_args, **_kwargs) -> None:
            return None

        monkeypatch.setattr(
            "app.services.inbound_reply.runtime.fetch_received_email", fake_fetch
        )
        monkeypatch.setattr(
            "app.services.inbound_reply.runtime.send_notification", fake_notification
        )
        receipt_payload = {
            "data": {
                "email_id": "received-north-star-lab",
                "from": recipient,
                "to": [reply_to],
                "subject": "Re: NX-500 Industrial Pump",
                "message_id": "<buyer-north-star-reply@example.test>",
                "attachments": [],
            }
        }
        async with factory() as db:
            reply, queued, created = await ingest_resend_receipt(
                db,
                payload=receipt_payload,
                provider_event_id="north-star-inbound-event",
                raw_payload_sha256="a" * 64,
            )
            await db.commit()
            duplicate_reply, queued_again, created_again = await ingest_resend_receipt(
                db,
                payload=receipt_payload,
                provider_event_id="north-star-inbound-event",
                raw_payload_sha256="a" * 64,
            )
            assert reply is not None and queued and created
            assert duplicate_reply is not None and duplicate_reply.id == reply.id
            assert not queued_again and not created_again
            reply_id = reply.id
        await run_inbound_reply_fetch(reply_id)
        async with factory() as db:
            inbound = await db.get(InboundReply, reply_id)
            assert inbound is not None
            assert inbound.classification == "rfq"
            assert inbound.status == "handed_off"
            handoffs = (
                await db.exec(
                    select(SalesHandoff).where(
                        SalesHandoff.inbound_reply_id == reply_id
                    )
                )
            ).all()
            assert len(handoffs) == 1
            handoff_id = handoffs[0].id
        milestones.append(
            {
                "stage": "reply_classified_and_handed_off",
                "inbound_reply_id": str(reply_id),
                "sales_handoff_id": str(handoff_id),
            }
        )

        token = await admin_token_for_tenant(tenant.id)
        other_token = await admin_token_for_tenant(other.id)
        accepted = await http_client.post(
            f"/api/v1/tracking/replies/{reply_id}/handoff",
            headers=_auth(token),
            json={"note": "Sales accepted the qualified reply"},
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["id"] == str(handoff_id)
        assert accepted.json()["status"] == "new"
        accepted = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/accept",
            headers=_auth(token),
            json={"note": "Sales accepted the qualified reply"},
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "accepted"

        converted = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/convert-to-rfq",
            headers=_auth(token),
            json={"note": "Buyer explicitly requested 500 units"},
        )
        assert converted.status_code == 200, converted.text
        rfq_id = converted.json()["rfq_id"]
        converted_again = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/convert-to-rfq",
            headers=_auth(token),
            json={"note": "Idempotent retry"},
        )
        assert converted_again.status_code == 200
        assert converted_again.json()["rfq_id"] == rfq_id

        attribution = await http_client.get(
            f"/api/v1/tracking/rfqs/{rfq_id}/attribution", headers=_auth(token)
        )
        assert attribution.status_code == 200, attribution.text
        assert attribution.json()["attribution_type"] == "direct"
        assert attribution.json()["lineage"]["inbound_reply_id"] == str(reply_id)
        isolated = await http_client.get(
            f"/api/v1/tracking/rfqs/{rfq_id}/attribution",
            headers=_auth(other_token),
        )
        assert isolated.status_code == 404

        won = await http_client.put(
            f"/api/v1/tracking/rfqs/{rfq_id}/status",
            headers=_auth(token),
            json={
                "status": "won",
                "reason": "North Star lab conversion",
                "deal_amount": "25000.00",
                "deal_currency": "USD",
            },
        )
        assert won.status_code == 200, won.text
        funnel = await http_client.get(
            "/api/v1/tracking/growth-funnel?days=30", headers=_auth(token)
        )
        assert funnel.status_code == 200, funnel.text
        layers = {row["stage"]: row["count"] for row in funnel.json()["layers"]}
        assert layers["tracked_visitors"] >= 1
        assert layers["replied"] >= 1
        assert layers["rfq"] >= 1
        assert layers["won"] >= 1

        async with factory() as db:
            rfq = await db.get(RFQRequest, uuid.UUID(rfq_id))
            assert rfq is not None and rfq.tenant_id == tenant.id
            assert rfq.status == "won"
            assert (
                await db.exec(
                    select(func.count(OperationalJob.id)).where(
                        OperationalJob.tenant_id == tenant.id,
                        OperationalJob.idempotency_key.like(f"rfq:{rfq.id}:%"),
                    )
                )
            ).one() == 5
            assert (
                await db.exec(
                    select(func.count(NetworkObservation.id)).where(
                        NetworkObservation.tenant_id == other.id
                    )
                )
            ).one() == 0
        milestones.append(
            {
                "stage": "rfq_won_and_attributed",
                "rfq_id": rfq_id,
                "attribution_type": "direct",
                "deal_amount": "25000.00",
                "deal_currency": "USD",
            }
        )
        _write_success_report(milestones)
    finally:
        await engine.dispose()
