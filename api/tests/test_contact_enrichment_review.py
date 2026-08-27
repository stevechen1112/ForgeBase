"""Batch-3 contact-candidate privacy, provider, review and conversion gates."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlmodel import func, select

from app.api.v1.endpoints.contact_enrichment import (
    CandidateDecisionIn,
    ConvertCandidateIn,
    PersonaPolicyUpdate,
    convert_candidate,
    review_candidate,
)
from app.core.datetime import utcnow_naive
from app.models.company_identification import (
    CompanyIdentification,
    NetworkObservation,
    ProviderUsage,
)
from app.models.contact import Contact
from app.models.contact_enrichment import (
    ContactCandidate,
    ContactCandidateReview,
    ContactPersonaPolicy,
)
from app.models.user import User
from app.models.visitor import Visitor
from app.services.company_identification.privacy import delete_visitor_company_evidence
from app.services.contact_enrichment.jobs import enqueue_contact_enrichment_job
from app.services.contact_enrichment.providers.apollo import ApolloContactProvider
from app.services.contact_enrichment.providers.base import (
    ContactProviderCandidate,
    ContactProviderRetryableError,
    ContactSearchContext,
)
from app.services.contact_enrichment.providers.hunter import (
    HunterEmailVerificationProvider,
)
from app.services.contact_enrichment.providers.mock import (
    MockEmailVerificationProvider,
)
from app.services.contact_enrichment.runtime import (
    run_contact_enrichment_job,
    score_candidate,
)
from tests.conftest import _make_engine, requires_db


class _CollectingSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def test_contact_job_payload_has_only_company_reference() -> None:
    session = _CollectingSession()
    tenant_id, company_id = uuid.uuid4(), uuid.uuid4()
    job = enqueue_contact_enrichment_job(
        session,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        company_identification_id=company_id,
    )
    assert session.added == [job]
    assert json.loads(job.payload_json) == {"company_identification_id": str(company_id)}
    assert "email" not in job.payload_json.lower()
    assert "visitor" not in job.payload_json.lower()


def test_contact_candidate_model_never_has_plaintext_email_field() -> None:
    fields = ContactCandidate.model_fields
    assert "email" not in fields
    assert "business_email" not in fields
    assert {"email_ciphertext", "email_hash", "email_masked"}.issubset(fields)
    constraints = {item.name for item in ContactCandidate.__table__.constraints}
    assert "uq_contact_candidate_company_email" in constraints
    assert "ck_contact_candidate_verification" in constraints
    assert "ck_contact_candidate_status" in constraints


def test_persona_policy_requires_narrow_target_for_review_mode() -> None:
    with pytest.raises(ValidationError, match="target departments or titles"):
        PersonaPolicyUpdate(mode="review_only", target_departments=[], target_titles=[])
    with pytest.raises(ValidationError, match="provider is not configured"):
        PersonaPolicyUpdate(
            mode="review_only",
            contact_provider_name="not-installed",
            target_titles=["buyer"],
        )


def test_relevance_score_is_explainable_and_honors_exclusions() -> None:
    policy = ContactPersonaPolicy(
        tenant_id=uuid.uuid4(),
        target_departments=["procurement"],
        target_titles=["purchasing"],
        target_seniorities=["director"],
        target_locations=["japan"],
        excluded_title_terms=["intern"],
    )
    strong = ContactProviderCandidate(
        full_name="Business Buyer",
        business_email="buyer@acme.example",
        job_title="Purchasing Director",
        department="Procurement",
        seniority="Director",
        location="Japan",
    )
    score, reasons = score_candidate(strong, policy, product_interest_score=10)
    assert score == 100
    assert {"confirmed_company_domain", "target_title", "target_department", "company_journey_product_interest"}.issubset(reasons)

    excluded = ContactProviderCandidate(
        full_name="Student",
        business_email="student@acme.example",
        job_title="Procurement Intern",
    )
    assert score_candidate(excluded, policy) == (0, ["excluded_title"])


def _context() -> ContactSearchContext:
    return ContactSearchContext(
        tenant_id=uuid.uuid4(),
        company_identification_id=uuid.uuid4(),
        company_name="Acme",
        company_domain="acme.example",
        target_departments=("procurement",),
        target_titles=("buyer",),
        target_seniorities=("manager",),
        target_locations=("Japan",),
        limit=2,
    )


@pytest.mark.asyncio
async def test_apollo_adapter_never_requests_personal_email_or_phone_and_filters_domain() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("api_search"):
            assert request.headers["x-api-key"] == "test-key"
            assert request.url.params["q_organization_domains_list[]"] == "acme.example"
            return httpx.Response(200, headers={"x-request-id": "apollo-search"}, json={"people": [{"id": "person-1"}, {"id": "person-2"}]})
        assert request.url.params["reveal_personal_emails"] == "false"
        assert request.url.params["reveal_phone_number"] == "false"
        if request.url.params["id"] == "person-1":
            return httpx.Response(200, json={"person": {"id": "person-1", "name": "Buyer", "title": "Buyer", "email": "buyer@acme.example", "email_status": "verified"}})
        return httpx.Response(200, json={"person": {"id": "person-2", "name": "Personal", "email": "person@gmail.com"}})

    provider = ApolloContactProvider(api_key="test-key", transport=httpx.MockTransport(handler))
    provider._cost = Decimal("0.4")
    result = await provider.search(_context())
    assert result.request_id == "apollo-search"
    assert [row.business_email for row in result.candidates] == ["buyer@acme.example"]
    assert "gmail.com" not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"status": "valid", "score": 98}, "verified"),
        ({"status": "accept_all", "accept_all": True}, "catch_all"),
        ({"status": "invalid", "score": 0}, "invalid"),
        ({"status": "valid", "webmail": True}, "risky"),
    ],
)
async def test_hunter_adapter_normalizes_verification_status(payload, expected) -> None:
    provider = HunterEmailVerificationProvider(
        api_key="test-key",  # pragma: allowlist secret -- test fixture
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"data": payload})),
    )
    result = await provider.verify("buyer@acme.example")
    assert result.status == expected
    assert "buyer@" not in repr(result)


def _session_context(factory):
    @asynccontextmanager
    async def context():
        async with factory() as session:
            yield session

    return context


class _FailingContactProvider:
    name = "failing"

    def __init__(self) -> None:
        self.calls = 0

    async def search(self, _context):
        self.calls += 1
        raise ContactProviderRetryableError("temporary contact-provider failure")

    async def healthcheck(self) -> bool:
        return False

    def estimate_cost(self) -> Decimal:
        return Decimal("0.1")


@requires_db
@pytest.mark.asyncio
async def test_contact_provider_failures_are_audited_and_open_circuit(
    two_tenants, monkeypatch
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    provider = _FailingContactProvider()
    monkeypatch.setattr(
        "app.services.contact_enrichment.runtime.get_session_ctx",
        _session_context(factory),
    )
    monkeypatch.setattr(
        "app.services.contact_enrichment.runtime.get_contact_provider",
        lambda _: provider,
    )
    monkeypatch.setattr(
        "app.services.contact_enrichment.runtime.get_verification_provider",
        lambda _: MockEmailVerificationProvider(),
    )
    try:
        now = utcnow_naive()
        visitor_id, observation_id, company_id = (
            uuid.uuid4(),
            uuid.uuid4(),
            uuid.uuid4(),
        )
        async with factory() as db:
            db.add(Visitor(visitor_id=visitor_id, tenant_id=tenant.id))
            await db.flush()
            db.add(
                NetworkObservation(
                    id=observation_id,
                    tenant_id=tenant.id,
                    visitor_id=visitor_id,
                    ip_hash="c" * 64,
                    ip_masked="192.0.2.0/24",
                    ip_version=4,
                    policy_version="test",
                    dedupe_key=f"circuit:{observation_id}",
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
                    company_name="Circuit Co",
                    domain="circuit.example",
                    provider="test",
                    candidate_key="circuit",
                    confidence=0.9,
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
                    contact_provider_name="mock",
                    verification_provider_name="mock",
                    target_titles=["buyer"],
                    daily_provider_cost_limit=Decimal(10),
                )
            )
            await db.commit()

        for retry_count in range(5):
            with pytest.raises(ContactProviderRetryableError):
                await run_contact_enrichment_job(
                    company_id, retry_count=retry_count
                )
        with pytest.raises(ContactProviderRetryableError, match="circuit is open"):
            await run_contact_enrichment_job(company_id, retry_count=5)
        assert provider.calls == 5
        async with factory() as db:
            usage = (
                await db.exec(
                    select(ProviderUsage).where(
                        ProviderUsage.tenant_id == tenant.id,
                        ProviderUsage.operation == "contact_search",
                    )
                )
            ).all()
            assert len(usage) == 5
            assert all(row.response_status == "error" for row in usage)
            assert [row.retry_count for row in usage] == [0, 1, 2, 3, 4]
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_review_only_runtime_dedupes_encrypts_and_manual_conversion_has_no_visitor_link(two_tenants, monkeypatch) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    monkeypatch.setattr("app.services.contact_enrichment.runtime.get_session_ctx", _session_context(factory))
    try:
        now = utcnow_naive()
        visitor_id = uuid.uuid4()
        observation_id = uuid.uuid4()
        company_id = uuid.uuid4()
        actor_id = uuid.uuid4()
        async with factory() as db:
            db.add(User(id=actor_id, tenant_id=tenant.id, email=f"reviewer-{uuid.uuid4().hex[:8]}@test.invalid", hashed_password="test", full_name="Reviewer", role="admin"))
            db.add(Visitor(visitor_id=visitor_id, tenant_id=tenant.id, facet_product_interest=10, analytics_consent_status="granted"))
            await db.flush()
            db.add(NetworkObservation(id=observation_id, tenant_id=tenant.id, visitor_id=visitor_id, ip_hash="a" * 64, ip_masked="203.0.113.0/24", ip_version=4, eligibility_status="eligible", consent_state="granted", policy_version="test", dedupe_key=f"test:{observation_id}", observed_at=now, expires_at=now + timedelta(days=30)))
            await db.flush()
            db.add(CompanyIdentification(id=company_id, tenant_id=tenant.id, visitor_id=visitor_id, network_observation_id=observation_id, company_name="Acme", domain="acme.example", provider="mock", candidate_key="acme", confidence=0.95, confidence_band="high", match_method="test", status="confirmed", expires_at=now + timedelta(days=30)))
            db.add(ContactPersonaPolicy(tenant_id=tenant.id, mode="review_only", contact_provider_name="mock", verification_provider_name="mock", target_departments=["procurement", "engineering"], target_titles=["procurement", "engineering"], target_seniorities=["manager", "director"], min_relevance_score=60))
            await db.commit()

        assert await run_contact_enrichment_job(company_id) == 2
        assert await run_contact_enrichment_job(company_id) == 0

        async with factory() as db:
            rows = (await db.exec(select(ContactCandidate).where(ContactCandidate.tenant_id == tenant.id).order_by(ContactCandidate.full_name))).all()
            assert len(rows) == 2
            assert all("@acme.example" not in row.email_ciphertext for row in rows)
            assert all(row.email_masked.endswith("@acme.example") for row in rows)
            assert (await db.exec(select(func.count(ProviderUsage.id)).where(ProviderUsage.tenant_id == tenant.id))).one() == 3
            candidate = rows[0]
            actor = await db.get(User, actor_id)
            assert actor is not None
            await review_candidate(candidate.id, CandidateDecisionIn(decision="approve"), db, actor)
            dnc_candidate = rows[1]
            await review_candidate(
                dnc_candidate.id,
                CandidateDecisionIn(
                    decision="do_not_contact", reason_code="manual_request"
                ),
                db,
                actor,
            )
            await db.refresh(dnc_candidate)
            assert dnc_candidate.email_ciphertext == ""
            assert dnc_candidate.full_name == "Suppressed business contact"
            assert dnc_candidate.email_hash

        async with factory() as db:
            actor = await db.get(User, actor_id)
            assert actor is not None
            result = await convert_candidate(candidate.id, ConvertCandidateIn(note="approved persona"), db, actor)
            contact = await db.get(Contact, uuid.UUID(result["contact_id"]))
            assert contact is not None
            linked_visitors = (
                await db.exec(select(Visitor).where(Visitor.contact_id == contact.id))
            ).all()
            assert linked_visitors == []
            assert contact.source_type == "contact_candidate"
            assert contact.source_reference_id == candidate.id
            reviews = (await db.exec(select(ContactCandidateReview).where(ContactCandidateReview.contact_candidate_id == candidate.id))).all()
            assert [row.decision for row in reviews] == ["approve", "convert"]
            deleted = await delete_visitor_company_evidence(
                db, tenant_id=tenant.id, visitor_id=visitor_id
            )
            await db.commit()
            assert deleted["contact_candidates"] == 1
            retained = await db.get(ContactCandidate, candidate.id)
            retained_contact = await db.get(Contact, contact.id)
            assert retained is not None
            assert retained.company_identification_id is None
            assert retained.source_company_domain == "acme.example"
            assert retained_contact is not None
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_unapproved_invalid_and_do_not_contact_candidates_cannot_convert(two_tenants) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    try:
        now = utcnow_naive()
        actor_id = uuid.uuid4()
        visitor_id = uuid.uuid4()
        observation_id = uuid.uuid4()
        company_id = uuid.uuid4()
        async with factory() as db:
            db.add(User(id=actor_id, tenant_id=tenant.id, email=f"guard-{uuid.uuid4().hex[:8]}@test.invalid", hashed_password="test", full_name="Guard", role="admin"))
            db.add(Visitor(visitor_id=visitor_id, tenant_id=tenant.id))
            await db.flush()
            db.add(NetworkObservation(id=observation_id, tenant_id=tenant.id, visitor_id=visitor_id, ip_hash="b" * 64, ip_masked="198.51.100.0/24", ip_version=4, policy_version="test", dedupe_key=f"guard:{observation_id}", observed_at=now, expires_at=now + timedelta(days=30)))
            await db.flush()
            db.add(CompanyIdentification(id=company_id, tenant_id=tenant.id, visitor_id=visitor_id, network_observation_id=observation_id, company_name="Guard Co", domain="guard.example", provider="test", candidate_key="guard", confidence=0.9, confidence_band="high", match_method="test", status="confirmed", expires_at=now + timedelta(days=30)))
            db.add(ContactPersonaPolicy(tenant_id=tenant.id, mode="review_only", target_titles=["buyer"], min_relevance_score=60))
            await db.flush()
            for status, verification in (("candidate", "verified"), ("approved", "invalid"), ("do_not_contact", "verified")):
                row = ContactCandidate(tenant_id=tenant.id, company_identification_id=company_id, source_company_name="Guard Co", source_company_domain="guard.example", full_name=status, email_ciphertext="encrypted", email_hash=uuid.uuid4().hex * 2, email_masked="x***@guard.example", verification_status=verification, source_provider="test", relevance_score=100, status=status, expires_at=now + timedelta(days=30))
                db.add(row)
            await db.commit()

        async with factory() as db:
            candidate_ids = list(
                (
                    await db.exec(
                        select(ContactCandidate.id).where(
                            ContactCandidate.company_identification_id == company_id
                        )
                    )
                ).all()
            )
        for candidate_id in candidate_ids:
            async with factory() as db:
                actor = await db.get(User, actor_id)
                assert actor is not None
                with pytest.raises(HTTPException) as error:
                    await convert_candidate(candidate_id, ConvertCandidateIn(), db, actor)
                assert getattr(error.value, "status_code", None) == 409

        async with factory() as db:
            actor = await db.get(User, actor_id)
            dnc = (
                await db.exec(
                    select(ContactCandidate).where(
                        ContactCandidate.company_identification_id == company_id,
                        ContactCandidate.status == "do_not_contact",
                    )
                )
            ).first()
            assert actor is not None and dnc is not None
            with pytest.raises(HTTPException) as error:
                await review_candidate(
                    dnc.id,
                    CandidateDecisionIn(decision="reject", reason_code="override"),
                    db,
                    actor,
                )
            assert error.value.status_code == 409
    finally:
        await engine.dispose()
