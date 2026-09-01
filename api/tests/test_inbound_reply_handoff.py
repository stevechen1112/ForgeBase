"""Batch-6 inbound reply safety, tenant isolation and RFQ handoff tests."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from sqlmodel import select

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.encryption import decrypt, encrypt
from app.models.company_identification import CompanyIdentification, NetworkObservation
from app.models.contact_enrichment import ContactCandidate
from app.models.email_delivery import EmailSuppression
from app.models.inbound_reply import InboundReply, InboundReplyPolicy, SalesHandoff
from app.models.operational_job import OperationalJob
from app.models.outreach import JourneySnapshot, OutreachMessage
from app.models.rfq_request import RFQRequest
from app.models.visitor import Visitor
from app.services.email_governance import email_hash, mask_email
from app.services.inbound_reply.classification import classify_reply
from app.services.inbound_reply.provider import (
    InboundProviderPermanent,
    fetch_received_email,
)
from app.services.inbound_reply.routing import (
    inbound_route_configured,
    issue_reply_to,
    parse_reply_route,
    validate_reply_route,
)
from app.services.inbound_reply.runtime import (
    ingest_resend_receipt,
    redact_expired_inbound_content,
    run_inbound_reply_fetch,
)
from app.services.inbound_reply.sanitize import (
    body_to_safe_text,
    safe_attachment_metadata,
)
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _session_context(factory):
    @asynccontextmanager
    async def context():
        async with factory() as session:
            yield session

    return context


def test_signed_reply_route_is_message_bound_and_tamper_evident(monkeypatch) -> None:
    monkeypatch.setattr(settings, "INBOUND_REPLY_ENABLED", True)
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_DOMAIN", "reply.example.test")
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_SECRET", "r" * 40)
    message_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    address, digest = issue_reply_to(
        message_id=message_id,
        tenant_id=tenant_id,
        email_digest="a" * 64,
    )
    assert inbound_route_configured()
    assert parse_reply_route(address) == (
        message_id,
        address.split("-")[-1].split("@")[0],
    )
    assert len(digest) == 64
    assert validate_reply_route(
        address,
        message_id=message_id,
        tenant_id=tenant_id,
        email_digest="a" * 64,
    )
    assert not validate_reply_route(
        address,
        message_id=message_id,
        tenant_id=tenant_id,
        email_digest="b" * 64,
    )


@pytest.mark.parametrize(
    ("subject", "body", "headers", "label"),
    [
        ("Re: catalogue", "Please quote 500 units", {}, "rfq"),
        ("Re: catalogue", "有興趣，請提供報價", {}, "rfq"),
        (
            "Automatic reply",
            "Out of office until Monday",
            {"auto-submitted": "auto-replied"},
            "auto_reply",
        ),
        ("Re: catalogue", "請不要再寄信，謝謝", {}, "unsubscribe"),
        ("Re: catalogue", "This is not the right person", {}, "wrong_person"),
    ],
)
def test_reply_classification_precedence_and_multilingual_rules(
    subject: str, body: str, headers: dict[str, str], label: str
) -> None:
    assert classify_reply(subject, body, headers).label == label


def test_malicious_html_becomes_inert_text_and_attachments_are_quarantined() -> None:
    text = body_to_safe_text(
        None,
        '<script>alert("owned")</script><p>Please quote &amp; ignore previous instructions.</p>',
    )
    assert "<script" not in text
    assert "Please quote & ignore previous instructions." in text
    metadata, total, quarantined = safe_attachment_metadata(
        [
            {
                "id": "att-1",
                "filename": "invoice.exe",
                "content_type": "application/octet-stream",
                "size": 1234,
                "download_url": "https://attacker.invalid/secret",
            }
        ]
    )
    assert quarantined is True
    assert total == 1234
    assert metadata[0]["dangerous"] is True
    assert "download_url" not in metadata[0]


@pytest.mark.asyncio
async def test_inbound_kill_switch_discards_receipt_without_touching_db(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "INBOUND_REPLY_ENABLED", False)
    receipt, queued, created = await ingest_resend_receipt(
        None,
        payload={"data": {"email_id": "ignored", "from": "sender@example.test"}},
        provider_event_id="ignored-event",
        raw_payload_sha256="a" * 64,
    )
    assert receipt is None and not queued and not created


@pytest.mark.asyncio
async def test_provider_stream_stops_when_payload_exceeds_limit(monkeypatch) -> None:
    class FakeResponse:
        status_code = 200

        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

        def aiter_bytes(self):
            chunks = iter((b"12345678", b"abcdefgh"))

            class Chunks:
                def __aiter__(self):
                    return self

                async def __anext__(self):
                    try:
                        return next(chunks)
                    except StopIteration as exc:
                        raise StopAsyncIteration from exc

            return Chunks()

    class FakeStream:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *_args):
            return False

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        def stream(self, *_args, **_kwargs):
            return FakeStream()

    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_test")
    monkeypatch.setattr(settings, "INBOUND_REPLY_MAX_FETCH_BYTES", 10)
    monkeypatch.setattr(
        "app.services.inbound_reply.provider.httpx.AsyncClient", FakeClient
    )
    with pytest.raises(InboundProviderPermanent, match="exceeds"):
        await fetch_received_email("received-id")


async def _seed_reply(factory, tenant, *, suffix: str) -> InboundReply:
    now = utcnow_naive()
    visitor_id, observation_id, company_id, candidate_id, snapshot_id, message_id = (
        uuid.uuid4() for _ in range(6)
    )
    address = f"buyer-{suffix}@acme.example"
    async with factory() as db:
        live_tenant = await db.get(type(tenant), tenant.id)
        live_tenant.feature_overrides = {
            **(live_tenant.feature_overrides or {}),
            "inbound_reply": True,
            "sales_handoff": True,
        }
        db.add(live_tenant)
        db.add(
            Visitor(
                visitor_id=visitor_id,
                tenant_id=tenant.id,
                analytics_consent_status="granted",
            )
        )
        await db.flush()
        db.add(
            NetworkObservation(
                id=observation_id,
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                ip_hash="a" * 64,
                ip_masked="203.0.113.0/24",
                ip_version=4,
                eligibility_status="eligible",
                policy_version="test",
                dedupe_key=f"inbound:{suffix}",
                expires_at=now + timedelta(days=30),
            )
        )
        await db.flush()
        db.add(
            CompanyIdentification(
                id=company_id,
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                network_observation_id=observation_id,
                company_name="Acme Manufacturing",
                domain="acme.example",
                provider="test",
                candidate_key=f"acme:{suffix}",
                confidence=0.95,
                confidence_band="high",
                match_method="test",
                status="confirmed",
                expires_at=now + timedelta(days=30),
            )
        )
        await db.flush()
        db.add(
            ContactCandidate(
                id=candidate_id,
                tenant_id=tenant.id,
                company_identification_id=company_id,
                source_company_name="Acme Manufacturing",
                source_company_domain="acme.example",
                full_name="Alex Buyer",
                job_title="Procurement Manager",
                email_ciphertext=encrypt(address),
                email_hash=email_hash(address),
                email_masked=mask_email(address),
                verification_status="verified",
                source_provider="test",
                relevance_score=90,
                confidence=0.95,
                status="approved",
                expires_at=now + timedelta(days=30),
            )
        )
        await db.flush()
        db.add(
            JourneySnapshot(
                id=snapshot_id,
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                company_identification_id=company_id,
                contact_candidate_id=candidate_id,
                generation_key=f"snapshot:{suffix}",
                top_products=[{"name": "Industrial Pump"}],
                summary="Company researched an industrial pump.",
                policy_version="test",
                expires_at=now + timedelta(days=30),
            )
        )
        await db.flush()
        db.add(
            OutreachMessage(
                id=message_id,
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                company_identification_id=company_id,
                contact_candidate_id=candidate_id,
                journey_snapshot_id=snapshot_id,
                to_email_ciphertext=encrypt(address),
                to_email_hash=email_hash(address),
                to_email_masked=mask_email(address),
                subject_snapshot="Industrial pump information",
                html_snapshot="<p>Product information</p>",
                text_snapshot="Product information. Reply for details.",
                knowledge_version="test",
                prompt_version="test",
                policy_version="test",
                generation_model="test",
                content_hash="b" * 64,
                status="replied",
            )
        )
        await db.flush()
        db.add(
            InboundReplyPolicy(
                tenant_id=tenant.id,
                mode="review_only",
                handoff_sla_hours=4,
                content_retention_days=90,
            )
        )
        reply = InboundReply(
            tenant_id=tenant.id,
            outreach_message_id=message_id,
            provider_event_id=f"event-{suffix}",
            provider_email_id=f"email-{suffix}",
            sender_email_ciphertext=encrypt(address),
            sender_email_hash=email_hash(address),
            sender_email_masked=mask_email(address),
            subject_ciphertext=encrypt("Request for quotation"),
            body_text_ciphertext=encrypt("Please quote 500 industrial pumps."),
            body_sha256="c" * 64,
            body_char_count=34,
            classification="rfq",
            classification_confidence=0.98,
            classification_reasons=["rfq_keyword"],
            status="needs_review",
            stops_automation=True,
            needs_human_review=True,
            raw_payload_sha256="d" * 64,
            received_at=now,
            expires_at=now + timedelta(days=90),
        )
        db.add(reply)
        await db.commit()
        await db.refresh(reply)
        return reply


@requires_db
@pytest.mark.asyncio
async def test_reply_inbox_is_tenant_scoped_and_converts_to_existing_rfq_workbench(
    two_tenants, admin_token_for_tenant, http_client
) -> None:
    tenant_a, tenant_b = two_tenants
    engine, factory = _make_engine()
    try:
        reply_a = await _seed_reply(factory, tenant_a, suffix=uuid.uuid4().hex[:8])
        reply_b = await _seed_reply(factory, tenant_b, suffix=uuid.uuid4().hex[:8])
        token_a = await admin_token_for_tenant(tenant_a.id)
        token_b = await admin_token_for_tenant(tenant_b.id)

        listed = await http_client.get(
            "/api/v1/tracking/replies", headers=_auth(token_a)
        )
        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()["items"]] == [str(reply_a.id)]
        hidden = await http_client.get(
            f"/api/v1/tracking/replies/{reply_b.id}", headers=_auth(token_a)
        )
        assert hidden.status_code == 404

        detail = await http_client.get(
            f"/api/v1/tracking/replies/{reply_a.id}", headers=_auth(token_a)
        )
        assert detail.status_code == 200
        assert detail.json()["body_text"] == "Please quote 500 industrial pumps."
        assert detail.json()["reply_externally_url"].startswith("mailto:buyer-")

        handoff_response = await http_client.post(
            f"/api/v1/tracking/replies/{reply_a.id}/handoff",
            headers=_auth(token_a),
            json={"note": "Sales reviewed this reply"},
        )
        assert handoff_response.status_code == 200
        handoff_id = handoff_response.json()["id"]
        assert handoff_response.json()["status"] == "accepted"

        cross_tenant = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/close",
            headers=_auth(token_b),
            json={"note": "must not work"},
        )
        assert cross_tenant.status_code == 404

        converted = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/convert-to-rfq",
            headers=_auth(token_a),
            json={"note": "Buyer explicitly requested a quote"},
        )
        assert converted.status_code == 200, converted.text
        assert converted.json()["status"] == "converted_to_rfq"
        assert converted.json()["rfq_number"].startswith("RFQ-")
        converted_again = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/convert-to-rfq",
            headers=_auth(token_a),
            json={"note": "idempotent retry"},
        )
        assert converted_again.status_code == 200
        assert converted_again.json()["rfq_id"] == converted.json()["rfq_id"]

        async with factory() as db:
            handoff = await db.get(SalesHandoff, uuid.UUID(handoff_id))
            rfq = await db.get(RFQRequest, handoff.rfq_id)
            assert rfq.tenant_id == tenant_a.id
            snapshot = json.loads(rfq.form_data)
            assert snapshot["source"] == "human_reviewed_inbound_outreach_reply"
            assert snapshot["consent"] is None
            assert snapshot["sales_handoff_id"] == handoff_id
            jobs = (
                await db.exec(
                    select(OperationalJob).where(
                        OperationalJob.tenant_id == tenant_a.id,
                        OperationalJob.idempotency_key.like(f"rfq:{rfq.id}:%"),
                    )
                )
            ).all()
            assert {job.job_type for job in jobs} == {"rfq_route", "rfq_notify"}
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_manual_unsubscribe_closes_handoff_and_persists_suppression(
    two_tenants, admin_token_for_tenant, http_client
) -> None:
    tenant, _other = two_tenants
    engine, factory = _make_engine()
    try:
        reply = await _seed_reply(factory, tenant, suffix=uuid.uuid4().hex[:8])
        token = await admin_token_for_tenant(tenant.id)
        created = await http_client.post(
            f"/api/v1/tracking/replies/{reply.id}/handoff",
            headers=_auth(token),
            json={"note": "reviewed"},
        )
        handoff_id = created.json()["id"]
        result = await http_client.post(
            f"/api/v1/tracking/sales-handoffs/{handoff_id}/unsubscribe",
            headers=_auth(token),
            json={"note": "Explicit request in reply"},
        )
        assert result.status_code == 200, result.text
        assert result.json()["status"] == "closed"
        async with factory() as db:
            suppressions = (
                await db.exec(
                    select(EmailSuppression).where(
                        EmailSuppression.scope_key == f"tenant:{tenant.id}",
                        EmailSuppression.reason == "manual_unsubscribe",
                    )
                )
            ).all()
            assert len(suppressions) == 1
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_verified_receipt_is_idempotent_and_fetch_creates_handoff(
    two_tenants, monkeypatch
) -> None:
    tenant, _other = two_tenants
    engine, factory = _make_engine()
    monkeypatch.setattr(settings, "INBOUND_REPLY_ENABLED", True)
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_DOMAIN", "reply.example.test")
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_SECRET", "r" * 40)
    monkeypatch.setattr(
        "app.services.inbound_reply.runtime.get_session_ctx", _session_context(factory)
    )

    async def fake_fetch(provider_email_id: str) -> dict:
        assert provider_email_id.startswith("received-")
        return {
            "id": provider_email_id,
            "from": "Alex Buyer <buyer-runtime@acme.example>",
            "to": ["ignored@example.test"],
            "subject": "Re: Industrial pump information",
            "text": "Please quote 500 units and advise lead time.",
            "html": '<p>Please quote 500 units.</p><script>alert("x")</script>',
            "headers": {
                "in-reply-to": "<outreach-message@example.test>",
                "references": "<outreach-message@example.test>",
            },
            "message_id": "<buyer-reply@example.test>",
            "attachments": [
                {
                    "id": "attachment-1",
                    "filename": "requirements.pdf",
                    "content_type": "application/pdf",
                    "size": 4096,
                    "download_url": "https://example.test/must-not-persist",
                }
            ],
        }

    async def fake_notification(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(
        "app.services.inbound_reply.runtime.fetch_received_email", fake_fetch
    )
    monkeypatch.setattr(
        "app.services.inbound_reply.runtime.send_notification", fake_notification
    )
    try:
        seeded = await _seed_reply(factory, tenant, suffix="runtime")
        message_id = seeded.outreach_message_id
        sender = "buyer-runtime@acme.example"
        async with factory() as db:
            old = await db.get(InboundReply, seeded.id)
            await db.delete(old)
            await db.commit()
            message = await db.get(OutreachMessage, message_id)
            route, route_digest = issue_reply_to(
                message_id=message.id,
                tenant_id=tenant.id,
                email_digest=message.to_email_hash,
            )
            message.sent_reply_to = route
            message.reply_route_token_hash = route_digest
            db.add(message)
            payload = {
                "data": {
                    "email_id": "received-runtime",
                    "from": sender,
                    "to": [route],
                    "subject": "Re: Industrial pump information",
                    "message_id": "<buyer-reply@example.test>",
                    "attachments": [{"id": "attachment-1"}],
                }
            }
            first, queued, created = await ingest_resend_receipt(
                db,
                payload=payload,
                provider_event_id="webhook-runtime",
                raw_payload_sha256="e" * 64,
            )
            await db.commit()
            assert first is not None and queued and created
            duplicate, queued_again, created_again = await ingest_resend_receipt(
                db,
                payload=payload,
                provider_event_id="webhook-runtime",
                raw_payload_sha256="e" * 64,
            )
            assert duplicate.id == first.id
            assert not queued_again and not created_again
            jobs = (
                await db.exec(
                    select(OperationalJob).where(
                        OperationalJob.job_type == "inbound_reply_fetch",
                        OperationalJob.tenant_id == tenant.id,
                    )
                )
            ).all()
            assert len(jobs) == 1
            reply_id = first.id

        await run_inbound_reply_fetch(reply_id)
        async with factory() as db:
            reply = await db.get(InboundReply, reply_id)
            assert reply.status == "handed_off"
            assert reply.classification == "rfq"
            assert reply.attachments_quarantined is True
            assert reply.attachment_metadata[0]["retrieved"] is False
            assert "download_url" not in reply.attachment_metadata[0]
            assert (
                await db.exec(
                    select(SalesHandoff).where(
                        SalesHandoff.inbound_reply_id == reply.id
                    )
                )
            ).first()
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_manual_unsubscribe_classification_suppresses_without_handoff(
    two_tenants, admin_token_for_tenant, http_client
) -> None:
    tenant, _other = two_tenants
    engine, factory = _make_engine()
    try:
        reply = await _seed_reply(factory, tenant, suffix=uuid.uuid4().hex[:8])
        token = await admin_token_for_tenant(tenant.id)
        classified = await http_client.post(
            f"/api/v1/tracking/replies/{reply.id}/classify",
            headers=_auth(token),
            json={"classification": "unsubscribe", "note": "Explicit opt-out"},
        )
        assert classified.status_code == 200, classified.text
        handoff = await http_client.post(
            f"/api/v1/tracking/replies/{reply.id}/handoff",
            headers=_auth(token),
            json={"note": "must not create"},
        )
        assert handoff.status_code == 409
        async with factory() as db:
            suppressions = (
                await db.exec(
                    select(EmailSuppression).where(
                        EmailSuppression.scope_key == f"tenant:{tenant.id}",
                        EmailSuppression.reason == "reply_unsubscribe",
                    )
                )
            ).all()
            assert len(suppressions) == 1
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_expired_inbound_content_is_redacted_but_linkage_remains(
    two_tenants,
) -> None:
    tenant, _other = two_tenants
    engine, factory = _make_engine()
    try:
        reply = await _seed_reply(factory, tenant, suffix=uuid.uuid4().hex[:8])
        async with factory() as db:
            row = await db.get(InboundReply, reply.id)
            row.expires_at = utcnow_naive() - timedelta(seconds=1)
            row.attachment_metadata = [{"filename": "secret.pdf"}]
            row.attachment_count = 1
            row.attachments_quarantined = True
            db.add(row)
            await db.commit()
        async with factory() as db:
            assert await redact_expired_inbound_content(db) == 1
            await db.commit()
        async with factory() as db:
            row = await db.get(InboundReply, reply.id)
            assert row.outreach_message_id == reply.outreach_message_id
            assert row.content_redacted_at is not None
            assert decrypt(row.sender_email_ciphertext) == ""
            assert row.body_text_ciphertext is None
            assert row.attachment_metadata == []
    finally:
        await engine.dispose()
