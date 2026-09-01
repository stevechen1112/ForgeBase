"""Batch-2 eligibility, privacy, Shadow runtime, and API contracts."""

import ipaddress
import uuid
from contextlib import asynccontextmanager
from decimal import Decimal

import httpx
import pytest
from pydantic import ValidationError
from sqlmodel import func, select

from app.api.v1.endpoints.company_identification import GrowthPolicyUpdate
from app.models.company_identification import (
    CompanyIdentification,
    CompanyIdentificationMode,
    GrowthAutomationPolicy,
    NetworkEligibilityStatus,
    NetworkObservation,
    ProviderUsage,
)
from app.models.operational_job import OperationalJob
from app.models.tracking_event import TrackingEvent
from app.models.visitor import Visitor
from app.services.client_ip import resolve_client_ip
from app.services.company_identification.eligibility import (
    assess_network,
    maybe_create_network_observation,
)
from app.services.company_identification.privacy import delete_visitor_company_evidence
from app.services.company_identification.providers.base import (
    CompanyCandidate,
    CompanyLookupContext,
    CompanyLookupResult,
    CompanyProviderPermanentError,
    CompanyProviderRetryableError,
)
from app.services.company_identification.providers.pdl import PeopleDataLabsIPProvider
from app.services.company_identification.runtime import (
    confidence_band,
    run_company_identification_job,
    sanitize_provider_evidence,
)
from tests.conftest import _make_engine, requires_db


def test_untrusted_peer_cannot_forge_forwarded_for() -> None:
    trusted = (ipaddress.ip_network("10.0.0.0/8"),)
    assert resolve_client_ip("198.51.100.9", "8.8.8.8", trusted) == "198.51.100.9"


def test_trusted_proxy_chain_returns_nearest_untrusted_address() -> None:
    trusted = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("192.0.2.0/24"),
    )
    assert (
        resolve_client_ip("10.1.0.5", "8.8.8.8, 192.0.2.44", trusted)
        == "8.8.8.8"
    )
    # One malformed hop invalidates the complete forwarded chain.
    assert resolve_client_ip("10.1.0.5", "8.8.8.8, forged", trusted) == "10.1.0.5"


def test_network_assessment_rejects_non_public_and_bot_traffic() -> None:
    assert assess_network("8.8.8.8", "Mozilla/5.0").eligible is True

    private = assess_network("10.0.0.8", "Mozilla/5.0")
    assert private.eligible is False
    assert private.ineligible_reason == "non_public_network"

    bot = assess_network("8.8.4.4", "ExampleBot/1.0")
    assert bot.eligible is False
    assert bot.ineligible_reason == "bot"


def test_evidence_sanitizer_drops_likely_pii_and_raw_payloads() -> None:
    safe = sanitize_provider_evidence(
        {
            "domain": "acme.example",
            "match_reason": "business network",
            "ip_address": "8.8.8.8",
            "person_name": "Secret Person",
            "raw_payload": {"anything": "must not persist"},
            "clientIp": "8.8.4.4",
            "description": "A legitimate company description",
            "company_name": "Acme Corp",
            "signals": ["asn", "domain"],
        }
    )
    assert safe == {
        "domain": "acme.example",
        "match_reason": "business network",
        "description": "A legitimate company description",
        "company_name": "Acme Corp",
        "signals": ["asn", "domain"],
    }


def test_provider_contract_rejects_duplicate_keys_and_invalid_domains() -> None:
    first = CompanyCandidate(
        company_name="Acme",
        candidate_key=" acme ",
        confidence=0.9,
        match_method="network",
        domain="acme.example",
    )
    duplicate = CompanyCandidate(
        company_name="Acme Duplicate",
        candidate_key="acme",
        confidence=0.8,
        match_method="network",
        domain="duplicate.example",
    )
    with pytest.raises(ValueError, match="unique candidate_key"):
        CompanyLookupResult(
            provider="test",
            request_id="request",
            candidates=(first, duplicate),
        )
    with pytest.raises(ValueError, match="valid hostname"):
        CompanyCandidate(
            company_name="Bad",
            candidate_key="bad",
            confidence=0.8,
            match_method="network",
            domain="https://bad.example/path",
        )


def _pdl_provider(handler) -> PeopleDataLabsIPProvider:
    return PeopleDataLabsIPProvider(
        api_key="test-key",  # pragma: allowlist secret -- test fixture
        endpoint="https://api.peopledatalabs.com/v5/ip/enrich",
        estimated_cost=Decimal("0.25"),
        transport=httpx.MockTransport(handler),
    )


def _lookup_context() -> CompanyLookupContext:
    return CompanyLookupContext(
        tenant_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        ip_address="8.8.8.8",
    )


@pytest.mark.asyncio
async def test_pdl_adapter_normalizes_company_and_drops_person_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        assert request.url.params["return_person"] == "false"
        return httpx.Response(
            200,
            headers={"x-request-id": "pdl-request"},
            json={
                "status": 200,
                "data": {
                    "ip": {
                        "address": "8.8.8.8",
                        "metadata": {
                            "vpn": False,
                            "proxy": False,
                            "hosting": False,
                            "asn_domain": "acme.example",
                        },
                    },
                    "company": {
                        "id": "pdl-acme",
                        "display_name": "Acme Corp",
                        "website": "https://www.acme.example/about",
                        "confidence": "very high",
                        "street_address": "must not persist",
                    },
                    "person": {"full_name": "must not persist"},
                    "dataset_version": "2026w34",
                },
            },
        )

    result = await _pdl_provider(handler).identify_company(_lookup_context())
    assert result.request_id == "pdl-request"
    assert result.estimated_cost == Decimal("0.25")
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.company_name == "Acme Corp"
    assert candidate.domain == "www.acme.example"
    assert candidate.confidence == 0.95
    assert "person" not in repr(result)
    assert "8.8.8.8" not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 500, 503])
async def test_pdl_adapter_classifies_retryable_responses(status: int) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"retry-after": "17"}, json={"status": status})

    with pytest.raises(CompanyProviderRetryableError) as error:
        await _pdl_provider(handler).identify_company(_lookup_context())
    if status == 429:
        assert error.value.retry_after_seconds == 17


@pytest.mark.asyncio
async def test_pdl_adapter_treats_privacy_network_as_no_candidate() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": 200,
                "data": {
                    "ip": {"metadata": {"vpn": True}},
                    "company": {
                        "id": "unsafe",
                        "name": "VPN Exit",
                        "website": "vpn.example",
                        "confidence": "high",
                    },
                },
            },
        )

    result = await _pdl_provider(handler).identify_company(_lookup_context())
    assert result.candidates == ()
    assert result.metadata["is_vpn"] is True


@pytest.mark.asyncio
async def test_pdl_adapter_classifies_auth_and_malformed_payloads() -> None:
    auth_provider = _pdl_provider(
        lambda _: httpx.Response(401, json={"status": 401})
    )
    with pytest.raises(CompanyProviderPermanentError):
        await auth_provider.identify_company(_lookup_context())

    malformed_provider = _pdl_provider(
        lambda _: httpx.Response(200, content=b"not-json")
    )
    with pytest.raises(CompanyProviderRetryableError):
        await malformed_provider.identify_company(_lookup_context())


@pytest.mark.asyncio
async def test_pdl_adapter_classifies_timeout_without_leaking_ip() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(CompanyProviderRetryableError) as error:
        await _pdl_provider(handler).identify_company(_lookup_context())
    assert "8.8.8.8" not in str(error.value)


def test_shadow_policy_schema_blocks_unimplemented_modes_and_bad_thresholds() -> None:
    policy = GrowthPolicyUpdate(
        company_identification_mode="shadow",
        provider_name="mock",
        allowed_countries=["tw", "JP", "TW"],
    )
    assert policy.allowed_countries == ["TW", "JP"]

    with pytest.raises(ValidationError):
        GrowthPolicyUpdate(company_identification_mode="review_only")
    with pytest.raises(ValidationError):
        GrowthPolicyUpdate(
            company_identification_mode="shadow",
            medium_confidence_threshold=0.9,
            high_confidence_threshold=0.8,
        )
    with pytest.raises(ValidationError):
        GrowthPolicyUpdate(
            company_identification_mode="shadow",
            provider_name="not-installed",
        )


def test_confidence_bands_follow_tenant_policy() -> None:
    policy = GrowthAutomationPolicy(
        tenant_id=uuid.uuid4(),
        medium_confidence_threshold=0.65,
        high_confidence_threshold=0.9,
    )
    assert confidence_band(0.95, policy) == "high"
    assert confidence_band(0.7, policy) == "medium"
    assert confidence_band(0.2, policy) == "low"


class _CountingProvider:
    name = "counting"

    def __init__(self, cost: Decimal = Decimal("0.25")) -> None:
        self.calls = 0
        self.cost = cost

    async def identify_company(self, context: CompanyLookupContext) -> CompanyLookupResult:
        self.calls += 1
        return CompanyLookupResult(
            provider=self.name,
            request_id=f"counting:{context.observation_id}",
            candidates=(
                CompanyCandidate(
                    company_name="Acme Corp",
                    candidate_key="acme",
                    confidence=0.95,
                    match_method="test_network",
                    domain="acme.example",
                ),
            ),
            units=1,
            estimated_cost=self.cost,
        )

    async def healthcheck(self) -> bool:
        return True

    def estimate_cost(self) -> Decimal:
        return self.cost


async def _create_test_observation(
    db,
    *,
    tenant_id: uuid.UUID,
    visitor_id: uuid.UUID,
    ip: str = "8.8.8.8",
    country: str | None = "TW",
) -> NetworkObservation:
    visitor = Visitor(
        visitor_id=visitor_id,
        tenant_id=tenant_id,
        total_page_views=4,
        analytics_consent_status="granted",
    )
    db.add(visitor)
    await db.flush()
    event = TrackingEvent(
        tenant_id=tenant_id,
        visitor_id=visitor_id,
        event_name="product_view",
        ip_address=ip,
        country=country,
    )
    db.add(event)
    await db.flush()
    observation = await maybe_create_network_observation(
        db,
        tenant_id=tenant_id,
        visitor=visitor,
        source_event=event,
        client_ip=ip,
        analytics_consent=True,
        user_agent="Mozilla/5.0",
    )
    assert observation is not None
    await db.commit()
    return observation


def _test_session_context(factory):
    @asynccontextmanager
    async def context():
        async with factory() as session:
            yield session

    return context


@requires_db
@pytest.mark.asyncio
async def test_shadow_runtime_replay_cache_cost_guard_and_circuit(
    two_tenants,
    monkeypatch,
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    provider = _CountingProvider()
    monkeypatch.setattr(
        "app.services.company_identification.runtime.get_company_identification_provider",
        lambda _: provider,
    )
    monkeypatch.setattr(
        "app.services.company_identification.runtime.get_session_ctx",
        _test_session_context(factory),
    )
    try:
        async with factory() as db:
            db.add(
                GrowthAutomationPolicy(
                    tenant_id=tenant.id,
                    company_identification_mode=CompanyIdentificationMode.shadow.value,
                    provider_name="mock",
                    daily_provider_cost_limit=Decimal(10),
                )
            )
            await db.commit()
            first = await _create_test_observation(
                db,
                tenant_id=tenant.id,
                visitor_id=uuid.uuid4(),
            )
            second = await _create_test_observation(
                db,
                tenant_id=tenant.id,
                visitor_id=uuid.uuid4(),
            )

        await run_company_identification_job(first.id)
        await run_company_identification_job(first.id)
        await run_company_identification_job(second.id)
        assert provider.calls == 1

        async with factory() as db:
            statuses = (
                await db.exec(
                    select(ProviderUsage.response_status).where(
                        ProviderUsage.tenant_id == tenant.id
                    )
                )
            ).all()
            assert sorted(statuses) == ["cached_match", "matched"]
            assert (
                await db.exec(
                    select(func.count(CompanyIdentification.id)).where(
                        CompanyIdentification.tenant_id == tenant.id
                    )
                )
            ).one() == 2

            policy = await db.get(GrowthAutomationPolicy, tenant.id)
            assert policy is not None
            policy.daily_provider_cost_limit = Decimal("0.10")
            db.add(policy)
            guarded = await _create_test_observation(
                db,
                tenant_id=tenant.id,
                visitor_id=uuid.uuid4(),
                ip="1.1.1.1",
            )
        await run_company_identification_job(guarded.id)
        assert provider.calls == 1

        async with factory() as db:
            guarded_row = await db.get(NetworkObservation, guarded.id)
            assert guarded_row is not None
            assert guarded_row.ineligible_reason == "daily_cost_limit_exceeded"

            policy = await db.get(GrowthAutomationPolicy, tenant.id)
            assert policy is not None
            policy.daily_provider_cost_limit = Decimal(10)
            db.add(policy)
            circuit_observation = await _create_test_observation(
                db,
                tenant_id=tenant.id,
                visitor_id=uuid.uuid4(),
                ip="9.9.9.9",
            )
            for index in range(5):
                db.add(
                    ProviderUsage(
                        tenant_id=tenant.id,
                        provider=provider.name,
                        operation="company_identify",
                        request_key=f"failure:{index}",
                        response_status="error",
                    )
                )
            await db.commit()
        with pytest.raises(CompanyProviderRetryableError, match="circuit is open"):
            await run_company_identification_job(circuit_observation.id)
        assert provider.calls == 1
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_observation_quota_and_country_policy_block_jobs(two_tenants) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    try:
        async with factory() as db:
            policy = GrowthAutomationPolicy(
                tenant_id=tenant.id,
                company_identification_mode=CompanyIdentificationMode.shadow.value,
                provider_name="mock",
                daily_lookup_quota=0,
            )
            db.add(policy)
            await db.commit()
            quota_blocked = await _create_test_observation(
                db,
                tenant_id=tenant.id,
                visitor_id=uuid.uuid4(),
            )
            assert quota_blocked.ineligible_reason == "daily_quota_exceeded"

            policy.daily_lookup_quota = 100
            policy.allowed_countries = ["JP"]
            db.add(policy)
            await db.commit()
            country_blocked = await _create_test_observation(
                db,
                tenant_id=tenant.id,
                visitor_id=uuid.uuid4(),
                ip="1.1.1.1",
                country="TW",
            )
            assert country_blocked.ineligible_reason == "country_not_allowed"
            assert (
                await db.exec(
                    select(func.count(OperationalJob.id)).where(
                        OperationalJob.tenant_id == tenant.id,
                        OperationalJob.job_type == "company_identify",
                    )
                )
            ).one() == 0
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_shadow_runtime_is_deduplicated_and_records_provider_usage(
    two_tenants,
    monkeypatch,
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    monkeypatch.setattr(
        "app.services.company_identification.runtime.get_session_ctx",
        _test_session_context(factory),
    )
    try:
        visitor_id = uuid.uuid4()
        event_id = uuid.uuid4()
        async with factory() as db:
            db.add(
                GrowthAutomationPolicy(
                    tenant_id=tenant.id,
                    company_identification_mode=CompanyIdentificationMode.shadow.value,
                    provider_name="mock",
                )
            )
            visitor = Visitor(
                visitor_id=visitor_id,
                tenant_id=tenant.id,
                total_page_views=4,
                analytics_consent_status="granted",
            )
            event = TrackingEvent(
                event_id=event_id,
                tenant_id=tenant.id,
                visitor_id=visitor_id,
                event_name="product_view",
                ip_address="8.8.8.8",
            )
            db.add(visitor)
            await db.flush()
            db.add(event)
            await db.commit()

            observation = await maybe_create_network_observation(
                db,
                tenant_id=tenant.id,
                visitor=visitor,
                source_event=event,
                client_ip="8.8.8.8",
                analytics_consent=True,
                user_agent="Mozilla/5.0",
            )
            duplicate = await maybe_create_network_observation(
                db,
                tenant_id=tenant.id,
                visitor=visitor,
                source_event=event,
                client_ip="8.8.8.8",
                analytics_consent=True,
                user_agent="Mozilla/5.0",
            )
            await db.commit()

            assert observation is not None
            assert duplicate is not None
            assert duplicate.id == observation.id
            assert observation.eligibility_status == NetworkEligibilityStatus.eligible.value
            assert "8.8.8.8" not in observation.ip_masked
            assert (
                await db.exec(
                    select(func.count(NetworkObservation.id)).where(
                        NetworkObservation.tenant_id == tenant.id
                    )
                )
            ).one() == 1
            assert (
                await db.exec(
                    select(func.count(OperationalJob.id)).where(
                        OperationalJob.tenant_id == tenant.id,
                        OperationalJob.job_type == "company_identify",
                    )
                )
            ).one() == 1

        await run_company_identification_job(observation.id)

        async with factory() as db:
            usage = (
                await db.exec(
                    select(ProviderUsage).where(ProviderUsage.tenant_id == tenant.id)
                )
            ).all()
            assert len(usage) == 1
            assert usage[0].provider == "mock"
            assert usage[0].response_status == "no_match"

            deleted = await delete_visitor_company_evidence(
                db,
                tenant_id=tenant.id,
                visitor_id=visitor_id,
            )
            await db.commit()
            assert deleted == {
                "network_observations": 1,
                "contact_candidates": 0,
                "contact_jobs": 0,
                "contact_provider_usage": 0,
                "company_jobs": 1,
                "provider_usage": 1,
            }
            assert (
                await db.exec(
                    select(func.count(NetworkObservation.id)).where(
                        NetworkObservation.tenant_id == tenant.id
                    )
                )
            ).one() == 0
    finally:
        await engine.dispose()
