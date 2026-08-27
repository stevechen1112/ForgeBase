"""Batch-4 grounding plus Batch-5 human-approved delivery lifecycle."""

import base64
import hashlib
import hmac
import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta

import pytest
from app.api.v1.endpoints.outreach import (
    DeliveryActionIn,
    DraftDecisionIn,
    DraftRevisionIn,
    queue_message_send,
    review_message,
    revise_message,
    unsubscribe_one_click,
)
from app.api.v1.endpoints.webhooks import receive_resend_webhook
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.core.encryption import encrypt
from app.models.company_identification import CompanyIdentification, NetworkObservation
from app.models.contact_enrichment import ContactCandidate, ContactPersonaPolicy
from app.models.email_delivery import EmailDeliveryEvent, EmailSuppression
from app.models.operational_job import OperationalJob
from app.models.outreach import (
    JourneySnapshot,
    OutreachDeliveryPolicy,
    OutreachDraftPolicy,
    OutreachMessage,
    OutreachMessageReview,
)
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.models.tracking_event import TrackingEvent
from app.models.user import User
from app.models.visitor import Visitor
from app.services.company_identification.privacy import delete_visitor_company_evidence
from app.services.email_governance import email_hash, mask_email
from app.services.email_service import EmailDeliveryResult
from app.services.outreach.content_guard import (
    OutreachContentError,
    canonical_cta,
    validate_content,
)
from app.services.outreach.delivery import run_outreach_send_job
from app.services.outreach.errors import OutreachSendRetryable
from app.services.outreach.jobs import enqueue_journey_summarize_job
from app.services.outreach.runtime import (
    run_journey_summarize_job,
    run_outreach_draft_job,
)
from fastapi import HTTPException
from sqlalchemy import text
from sqlmodel import select
from starlette.requests import Request

from tests.conftest import _make_engine, requires_db


class _CollectingSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def _session_context(factory):
    @asynccontextmanager
    async def context():
        async with factory() as session:
            yield session

    return context


def test_outreach_models_keep_recipient_private_and_job_payload_has_no_pii() -> None:
    fields = OutreachMessage.model_fields
    assert {"sent_at", "provider_message_id", "send_idempotency_key"}.issubset(fields)
    assert "to_email" not in fields
    assert {"to_email_ciphertext", "to_email_hash", "to_email_masked"}.issubset(fields)
    session = _CollectingSession()
    tenant_id, candidate_id = uuid.uuid4(), uuid.uuid4()
    job = enqueue_journey_summarize_job(
        session, tenant_id=tenant_id, candidate_id=candidate_id
    )  # type: ignore[arg-type]
    assert session.added == [job]
    assert json.loads(job.payload_json) == {"contact_candidate_id": str(candidate_id)}
    assert "email" not in job.payload_json.lower()
    assert "visitor" not in job.payload_json.lower()


@pytest.mark.parametrize(
    "body",
    [
        "We noticed you visited our product page.",
        "The price is USD 100.",
        "Delivery in 5 days is guaranteed.",
        "As discussed in our previous conversation.",
        "Your visitor ID and IP address were recorded.",
    ],
)
def test_content_guard_blocks_tracking_and_unsupported_claims(body: str) -> None:
    with pytest.raises(OutreachContentError):
        validate_content(subject="Product information", body_without_cta=body)


def test_canonical_cta_is_one_clear_reply_action() -> None:
    cta = canonical_cta("en")
    assert cta.lower().count("reply") == 1
    assert "http" not in cta.lower()


@requires_db
@pytest.mark.asyncio
async def test_snapshot_grounding_and_human_approved_delivery_lifecycle(
    two_tenants, monkeypatch
) -> None:
    tenant, other = two_tenants
    engine, factory = _make_engine()
    monkeypatch.setattr(
        "app.services.outreach.runtime.get_session_ctx", _session_context(factory)
    )
    monkeypatch.setattr(
        "app.services.outreach.delivery.get_session_ctx", _session_context(factory)
    )
    try:
        now = utcnow_naive()
        visitor_id, observation_id, company_id, candidate_id, actor_id = (
            uuid.uuid4() for _ in range(5)
        )
        address = f"buyer-{uuid.uuid4().hex[:8]}@acme.example"
        async with factory() as db:
            tenant.feature_overrides = {
                **tenant.feature_overrides,
                "outreach_send": True,
            }
            db.add(tenant)
            db.add(
                User(
                    id=actor_id,
                    email=f"outreach-{uuid.uuid4().hex[:8]}@test.invalid",
                    hashed_password="test",  # pragma: allowlist secret -- test fixture
                    full_name="Reviewer",
                    role="admin",
                    is_superuser=True,
                )
            )
            db.add(
                Visitor(
                    visitor_id=visitor_id,
                    tenant_id=tenant.id,
                    analytics_consent_status="granted",
                    intent_score=72,
                    intent_stage="hot",
                    facet_product_interest=20,
                    facet_procurement_readiness=10,
                )
            )
            await db.flush()
            db.add(
                NetworkObservation(
                    id=observation_id,
                    tenant_id=tenant.id,
                    visitor_id=visitor_id,
                    ip_hash="d" * 64,
                    ip_masked="203.0.113.0/24",
                    ip_version=4,
                    eligibility_status="eligible",
                    consent_state="granted",
                    policy_version="test",
                    dedupe_key=f"draft:{observation_id}",
                    observed_at=now,
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
                    company_name="Acme",
                    domain="acme.example",
                    provider="test",
                    candidate_key="acme",
                    confidence=0.95,
                    confidence_band="high",
                    match_method="test",
                    status="confirmed",
                    expires_at=now + timedelta(days=30),
                )
            )
            db.add(
                ContactPersonaPolicy(
                    tenant_id=tenant.id,
                    mode="review_only",
                    target_titles=["buyer"],
                    min_relevance_score=60,
                )
            )
            db.add(
                OutreachDraftPolicy(
                    tenant_id=tenant.id,
                    mode="review_only",
                    allowed_languages=["en"],
                    lookback_days=30,
                    snapshot_retention_days=20,
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
                ContactCandidate(
                    id=candidate_id,
                    tenant_id=tenant.id,
                    company_identification_id=company_id,
                    source_company_name="Acme",
                    source_company_domain="acme.example",
                    full_name="Business Buyer",
                    job_title="Buyer",
                    email_ciphertext=encrypt(address),
                    email_hash=email_hash(address),
                    email_masked=mask_email(address),
                    verification_status="verified",
                    source_provider="test",
                    relevance_score=90,
                    status="approved",
                    expires_at=now + timedelta(days=25),
                )
            )
            published_category = ProductCategory(
                tenant_id=tenant.id,
                category_name="Fasteners",
                slug=f"fasteners-{uuid.uuid4().hex[:6]}",
                status="published",
                locale="en",
            )
            other_category = ProductCategory(
                tenant_id=other.id,
                category_name="Other",
                slug=f"other-{uuid.uuid4().hex[:6]}",
                status="published",
                locale="en",
            )
            db.add(published_category)
            db.add(other_category)
            await db.flush()
            published = Product(
                tenant_id=tenant.id,
                product_name="Published Bolt",
                slug=f"published-{uuid.uuid4().hex[:6]}",
                model_number=f"PB-{uuid.uuid4().hex[:6]}",
                short_description="Published public description",
                category_id=published_category.id,
                status="published",
                locale="en",
                published_at=now,
            )
            draft = Product(
                tenant_id=tenant.id,
                product_name="Secret Draft",
                slug=f"draft-{uuid.uuid4().hex[:6]}",
                model_number=f"SD-{uuid.uuid4().hex[:6]}",
                short_description="Unpublished claim",
                category_id=published_category.id,
                status="draft",
                locale="en",
            )
            foreign = Product(
                tenant_id=other.id,
                product_name="Other Tenant Product",
                slug=f"foreign-{uuid.uuid4().hex[:6]}",
                model_number=f"OT-{uuid.uuid4().hex[:6]}",
                short_description="Foreign",
                category_id=other_category.id,
                status="published",
                locale="en",
                published_at=now,
            )
            db.add(published)
            db.add(draft)
            db.add(foreign)
            await db.flush()
            valid_event = TrackingEvent(
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                event_name="product_view",
                timestamp=now,
                page_type="product",
                page_id=published.id,
                locale="en",
            )
            download_event = TrackingEvent(
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                event_name="spec_download",
                timestamp=now,
                page_type="product",
                page_id=published.id,
                locale="en",
            )
            draft_event = TrackingEvent(
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                event_name="product_view",
                timestamp=now,
                page_type="product",
                page_id=draft.id,
                locale="en",
            )
            foreign_event = TrackingEvent(
                tenant_id=other.id,
                visitor_id=visitor_id,
                event_name="product_view",
                timestamp=now,
                page_type="product",
                page_id=foreign.id,
                locale="en",
            )
            deleted_event = TrackingEvent(
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                event_name="product_view",
                timestamp=now,
                page_type="product",
                page_id=uuid.uuid4(),
                locale="en",
            )
            db.add(valid_event)
            db.add(download_event)
            db.add(draft_event)
            db.add(foreign_event)
            db.add(deleted_event)
            await db.commit()

        snapshot_id = await run_journey_summarize_job(candidate_id)
        assert await run_journey_summarize_job(candidate_id) == snapshot_id
        async with factory() as db:
            snapshot = await db.get(JourneySnapshot, snapshot_id)
            assert snapshot is not None
            assert [item["title"] for item in snapshot.top_products] == [
                "Published Bolt"
            ]
            assert [item["title"] for item in snapshot.downloads] == ["Published Bolt"]
            assert set(snapshot.evidence_event_ids) == {
                str(valid_event.event_id),
                str(download_event.event_id),
            }
            assert "Secret Draft" not in json.dumps(snapshot.knowledge_references)
            assert "Other Tenant Product" not in json.dumps(
                snapshot.knowledge_references
            )
            draft_job = (
                await db.exec(
                    select(OperationalJob).where(
                        OperationalJob.job_type == "outreach_draft",
                        OperationalJob.tenant_id == tenant.id,
                    )
                )
            ).one()
            assert (
                len(
                    (
                        await db.exec(
                            select(JourneySnapshot).where(
                                JourneySnapshot.contact_candidate_id == candidate_id
                            )
                        )
                    ).all()
                )
                == 1
            )
            assert (
                len(
                    (
                        await db.exec(
                            select(OperationalJob).where(
                                OperationalJob.job_type == "outreach_draft",
                                OperationalJob.tenant_id == tenant.id,
                            )
                        )
                    ).all()
                )
                == 1
            )

        message_id = await run_outreach_draft_job(snapshot_id, candidate_id)
        async with factory() as db:
            message = await db.get(OutreachMessage, message_id)
            actor = await db.get(User, actor_id)
            assert message is not None and actor is not None
            assert message.status == "pending_review"
            assert message.to_email_masked == mask_email(address)
            assert address not in repr(message)
            assert "noticed" not in message.text_snapshot.lower()
            assert message.text_snapshot.count(canonical_cta("en")) == 1
            jobs_before = len(
                (
                    await db.exec(
                        select(OperationalJob).where(
                            OperationalJob.tenant_id == tenant.id
                        )
                    )
                ).all()
            )
            product = await db.get(Product, published.id)
            assert product is not None
            product.status = "draft"
            db.add(product)
            await db.commit()
            with pytest.raises(HTTPException) as unpublished:
                await review_message(
                    message.id, DraftDecisionIn(decision="approve"), db, actor
                )
            assert unpublished.value.status_code == 409
            product.status = "published"
            db.add(product)
            visitor = await db.get(Visitor, visitor_id)
            assert visitor is not None
            visitor.analytics_consent_status = "denied"
            db.add(visitor)
            await db.commit()
            with pytest.raises(HTTPException) as no_consent:
                await review_message(
                    message.id, DraftDecisionIn(decision="approve"), db, actor
                )
            assert no_consent.value.status_code == 409
            visitor.analytics_consent_status = "granted"
            db.add(visitor)
            suppression = EmailSuppression(
                scope_key="global",
                email_hash=email_hash(address),
                email_masked=mask_email(address),
                reason="manual",
                active=True,
            )
            db.add(suppression)
            await db.commit()
            with pytest.raises(HTTPException) as suppressed:
                await review_message(
                    message.id, DraftDecisionIn(decision="approve"), db, actor
                )
            assert suppressed.value.status_code == 409
            suppression.active = False
            db.add(suppression)
            await db.commit()
            monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", True)
            monkeypatch.setattr(settings, "OUTREACH_SEND_ENABLED", True)
            monkeypatch.setattr(settings, "RESEND_API_KEY", "test-key")
            monkeypatch.setattr(
                settings, "OUTREACH_PUBLIC_BASE_URL", "https://api.example.test"
            )
            monkeypatch.setattr(
                settings, "OUTREACH_UNSUBSCRIBE_SECRET", "batch-five-secret-" + "x" * 32
            )
            result = await review_message(
                message.id, DraftDecisionIn(decision="approve"), db, actor
            )
            assert result["send_available"] is True
            jobs_after = len(
                (
                    await db.exec(
                        select(OperationalJob).where(
                            OperationalJob.tenant_id == tenant.id
                        )
                    )
                ).all()
            )
            assert jobs_after == jobs_before
            assert draft_job.status == "pending"
            monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", "")
            with pytest.raises(HTTPException) as missing_webhook:
                await queue_message_send(message.id, DeliveryActionIn(), db, actor)
            assert missing_webhook.value.status_code == 409
            webhook_key = b"w" * 32
            monkeypatch.setattr(
                settings,
                "RESEND_WEBHOOK_SECRET",
                "whsec_" + base64.b64encode(webhook_key).decode(),
            )
            queued = await queue_message_send(
                message.id, DeliveryActionIn(note="approved pilot"), db, actor
            )
            assert queued["message"]["status"] == "queued"
            duplicate = await queue_message_send(
                message.id, DeliveryActionIn(), db, actor
            )
            assert duplicate["duplicate"] is True

        calls: list[str | None] = []
        provider_payloads: list[dict] = []

        async def provider_attempt(**kwargs):
            calls.append(kwargs.get("idempotency_key"))
            provider_payloads.append(kwargs)
            if len(calls) == 1:
                return EmailDeliveryResult(
                    False, False, False, "resend", error="request_failed"
                )
            return EmailDeliveryResult(
                True, True, False, "resend", message_id="resend-batch5-message"
            )

        monkeypatch.setattr(
            "app.services.outreach.delivery.send_email_result", provider_attempt
        )
        with pytest.raises(OutreachSendRetryable):
            await run_outreach_send_job(message_id)
        async with factory() as db:
            first_attempt = await db.get(OutreachMessage, message_id)
            assert first_attempt is not None and first_attempt.sending_at is not None
            first_sending_at = first_attempt.sending_at
            db.add(
                EmailDeliveryEvent(
                    provider="resend",
                    provider_event_id=f"early-{uuid.uuid4()}",
                    provider_message_id="resend-batch5-message",
                    event_type="email.clicked",
                    recipient_hash=email_hash(address),
                    recipient_masked=mask_email(address),
                    is_unknown_message=True,
                    occurred_at=utcnow_naive(),
                )
            )
            await db.commit()
        await run_outreach_send_job(message_id, retry_count=1)
        assert len(calls) == 2 and calls[0] == calls[1]
        for key in (
            "subject",
            "html_body",
            "text_body",
            "from_name",
            "from_email",
            "message_headers",
        ):
            assert provider_payloads[0][key] == provider_payloads[1][key]
        async with factory() as db:
            sent = await db.get(OutreachMessage, message_id)
            assert sent is not None
            assert sent.status == "clicked"
            assert sent.sending_at == first_sending_at
            assert sent.provider_message_id == "resend-batch5-message"
            assert (
                sent.sent_text_snapshot and "Stop receiving" in sent.sent_text_snapshot
            )
            assert (
                sent.sent_headers["List-Unsubscribe-Post"]
                == "List-Unsubscribe=One-Click"
            )
            event_id = f"delivery-{uuid.uuid4()}"
            timestamp = str(int(time.time()))
            raw = json.dumps(
                {
                    "type": "email.delivered",
                    "created_at": utcnow_naive().isoformat() + "Z",
                    "data": {
                        "email_id": "resend-batch5-message",
                        "to": [address],
                    },
                }
            ).encode()
            signed = f"{event_id}.{timestamp}.".encode() + raw
            signature = base64.b64encode(
                hmac.new(webhook_key, signed, hashlib.sha256).digest()
            ).decode()

            async def receive():
                return {"type": "http.request", "body": raw, "more_body": False}

            scope = {
                "type": "http",
                "method": "POST",
                "path": "/api/v1/webhooks/resend",
                "headers": [
                    (b"svix-id", event_id.encode()),
                    (b"svix-timestamp", timestamp.encode()),
                    (b"svix-signature", f"v1,{signature}".encode()),
                ],
            }
            assert (await receive_resend_webhook(Request(scope, receive), db))[
                "duplicate"
            ] is False
            assert (await receive_resend_webhook(Request(scope, receive), db))[
                "duplicate"
            ] is True
            await db.refresh(sent)
            assert sent.status == "clicked"
            linked_event = (
                await db.exec(
                    select(EmailDeliveryEvent).where(
                        EmailDeliveryEvent.provider_event_id == event_id,
                        EmailDeliveryEvent.outreach_message_id == sent.id,
                        EmailDeliveryEvent.tenant_id == tenant.id,
                    )
                )
            ).first()
            assert linked_event is not None and linked_event.is_unknown_message is False
            token = sent.sent_headers["List-Unsubscribe"].strip("<>").rsplit("/", 1)[-1]
            unsubscribed = await unsubscribe_one_click(token, db)
            assert unsubscribed["unsubscribed"] is True
            assert (await unsubscribe_one_click(token, db))["duplicate"] is True
            await db.refresh(sent)
            assert sent.status == "unsubscribed"
            tenant_suppression = (
                await db.exec(
                    select(EmailSuppression).where(
                        EmailSuppression.scope_key == f"tenant:{tenant.id}",
                        EmailSuppression.email_hash == email_hash(address),
                        EmailSuppression.active.is_(True),
                    )
                )
            ).first()
            assert tenant_suppression is not None
            await db.delete(suppression)
            await db.commit()
            deleted = await delete_visitor_company_evidence(
                db, tenant_id=tenant.id, visitor_id=visitor_id
            )
            await db.commit()
            assert deleted["outreach_jobs"] == 1
            assert deleted["preserved_business_company_evidence"] == 1
            db.expire_all()
            # An anonymous visitor is not the same person as the company contact.
            # Preserve the already-sent business communication and its evidence.
            assert await db.get(JourneySnapshot, snapshot_id) is not None
            assert await db.get(OutreachMessage, message_id) is not None

            await db.exec(
                text(
                    "UPDATE network_observations SET observed_at = NOW() - INTERVAL '40 days', "
                    "expires_at = NOW() - INTERVAL '1 day' WHERE id = :id"
                ),
                params={"id": str(observation_id)},
            )
            await db.exec(
                text(
                    "UPDATE contact_candidates SET created_at = NOW() - INTERVAL '40 days', "
                    "expires_at = NOW() - INTERVAL '1 day' WHERE id = :id"
                ),
                params={"id": str(candidate_id)},
            )
            await db.exec(
                text(
                    "UPDATE journey_snapshots SET generated_at = NOW() - INTERVAL '40 days', "
                    "expires_at = NOW() - INTERVAL '1 day' WHERE id = :id"
                ),
                params={"id": str(snapshot_id)},
            )
            await db.commit()
            from app.services.privacy_retention import purge_expired_analytics

            retained = await purge_expired_analytics(db, commit=False)
            await db.commit()
            assert retained["preserved_business_company_evidence"] >= 1
            assert await db.get(ContactCandidate, candidate_id) is not None
            assert await db.get(JourneySnapshot, snapshot_id) is not None
            assert await db.get(OutreachMessage, message_id) is not None
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_revision_is_new_snapshot_original_is_immutable_and_bad_claim_is_rejected(
    two_tenants,
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    try:
        now = utcnow_naive()
        (
            actor_id,
            visitor_id,
            observation_id,
            company_id,
            candidate_id,
            snapshot_id,
            message_id,
        ) = (uuid.uuid4() for _ in range(7))
        async with factory() as db:
            db.add(
                User(
                    id=actor_id,
                    email=f"revision-{uuid.uuid4().hex[:8]}@test.invalid",
                    hashed_password="test",  # pragma: allowlist secret -- test fixture
                    full_name="Reviewer",
                    role="admin",
                    is_superuser=True,
                )
            )
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
                    ip_hash="e" * 64,
                    ip_masked="198.51.100.0/24",
                    ip_version=4,
                    policy_version="test",
                    dedupe_key=f"revision:{observation_id}",
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
                    company_name="Revision Co",
                    domain="revision.example",
                    provider="test",
                    candidate_key="revision",
                    confidence=0.95,
                    confidence_band="high",
                    match_method="test",
                    status="confirmed",
                    expires_at=now + timedelta(days=30),
                )
            )
            db.add(
                ContactCandidate(
                    id=candidate_id,
                    tenant_id=tenant.id,
                    company_identification_id=company_id,
                    source_company_name="Revision Co",
                    source_company_domain="revision.example",
                    full_name="Buyer",
                    email_ciphertext=encrypt("buyer@revision.example"),
                    email_hash=email_hash("buyer@revision.example"),
                    email_masked=mask_email("buyer@revision.example"),
                    verification_status="verified",
                    source_provider="test",
                    relevance_score=90,
                    status="approved",
                    expires_at=now + timedelta(days=30),
                )
            )
            db.add(
                JourneySnapshot(
                    id=snapshot_id,
                    tenant_id=tenant.id,
                    visitor_id=visitor_id,
                    company_identification_id=company_id,
                    contact_candidate_id=candidate_id,
                    generation_key=f"revision:{snapshot_id}",
                    summary="Published product interest",
                    evidence_event_ids=[str(uuid.uuid4())],
                    knowledge_references=[
                        {
                            "entity_type": "product",
                            "entity_id": str(uuid.uuid4()),
                            "title": "Published Bolt",
                            "locale": "en",
                        }
                    ],
                    policy_version="v1",
                    expires_at=now + timedelta(days=20),
                )
            )
            original_text = f"Hello Buyer,\n\nWe can share published information.\n\n{canonical_cta('en')}"
            original_html = "<p>Hello Buyer,</p><p>We can share published information.</p><p>CTA</p>"
            digest = (
                __import__("hashlib")
                .sha256(f"Original\n{original_text}\n{original_html}".encode())
                .hexdigest()
            )
            db.add(
                OutreachMessage(
                    id=message_id,
                    tenant_id=tenant.id,
                    visitor_id=visitor_id,
                    company_identification_id=company_id,
                    contact_candidate_id=candidate_id,
                    journey_snapshot_id=snapshot_id,
                    revision_no=1,
                    language="en",
                    to_email_ciphertext=encrypt("buyer@revision.example"),
                    to_email_hash=email_hash("buyer@revision.example"),
                    to_email_masked=mask_email("buyer@revision.example"),
                    subject_snapshot="Original",
                    html_snapshot=original_html,
                    text_snapshot=original_text,
                    knowledge_version="v1",
                    prompt_version="v1",
                    policy_version="v1",
                    generation_model="test",
                    content_hash=digest,
                    status="pending_review",
                )
            )
            await db.commit()

        async with factory() as db:
            actor = await db.get(User, actor_id)
            assert actor is not None
            with pytest.raises(HTTPException) as error:
                await revise_message(
                    message_id,
                    DraftRevisionIn(
                        subject="Offer",
                        body_without_cta="The price is USD 100.",
                        note="bad",
                    ),
                    db,
                    actor,
                )
            assert error.value.status_code == 422
            revised = await revise_message(
                message_id,
                DraftRevisionIn(
                    subject="Published product information",
                    body_without_cta="Hello Buyer,\n\nWe can share the relevant published information.",
                    note="clarified",
                ),
                db,
                actor,
            )
            assert revised["revision_no"] == 2
            original = await db.get(OutreachMessage, message_id)
            assert original is not None
            assert original.subject_snapshot == "Original"
            assert original.status == "cancelled"
            reviews = (
                await db.exec(
                    select(OutreachMessageReview).where(
                        OutreachMessageReview.outreach_message_id
                        == uuid.UUID(revised["id"])
                    )
                )
            ).all()
            assert [row.action for row in reviews] == ["revised"]
            rejected = await review_message(
                uuid.UUID(revised["id"]),
                DraftDecisionIn(decision="reject", reason_code="stale_evidence"),
                db,
                actor,
            )
            assert rejected["status"] == "rejected"
            with pytest.raises(HTTPException) as old_review:
                await review_message(
                    message_id, DraftDecisionIn(decision="approve"), db, actor
                )
            assert old_review.value.status_code == 409
    finally:
        await engine.dispose()
