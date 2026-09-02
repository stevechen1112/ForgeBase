"""Batch-1 contracts for company-identification foundations."""

import json
import uuid
from datetime import timedelta

import pytest

from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.models.company_identification import (
    CompanyIdentification,
    IdentificationReviewDecision,
    IdentificationStatus,
    NetworkEligibilityStatus,
    NetworkObservation,
    ProviderUsage,
)
from app.models.tenant import Tenant
from app.services.capability_access import resolve_tenant_features
from app.services.company_identification.jobs import enqueue_company_identification_job
from app.services.company_identification.providers import (
    CompanyCandidate,
    CompanyLookupContext,
    MockCompanyIdentificationProvider,
    UnsupportedCompanyIdentificationProvider,
    available_provider_names,
    get_company_identification_provider,
)


class _CollectingSession:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)


def test_growth_feature_flags_are_locked_off_during_foundation_stage() -> None:
    tenant = Tenant(
        name="Pilot",
        slug="pilot-growth",
        feature_overrides={
            "company_identification": True,
            "contact_enrichment": True,
            "journey_personalization": True,
            "outreach_review": True,
            "outreach_send": True,
            "inbound_reply": True,
            "sales_handoff": True,
        },
    )

    resolved = resolve_tenant_features(tenant)

    for feature in tenant.feature_overrides:
        # Reviewed receive/handoff and human-approved send are available while
        # provider-data stages remain locked behind external-quality gates.
        assert resolved[feature] is (
            feature
            in {
                "outreach_send",
                "inbound_reply",
                "sales_handoff",
            }
        )


def test_network_observation_is_privacy_minimised() -> None:
    fields = NetworkObservation.model_fields
    assert "ip_address" not in fields
    assert "raw_ip" not in fields
    assert {"ip_hash", "ip_masked", "source_event_id"}.issubset(fields)

    now = utcnow_naive()
    observation = NetworkObservation(
        tenant_id=uuid.uuid4(),
        visitor_id=uuid.uuid4(),
        ip_hash="a" * 64,
        ip_masked="203.0.113.0/24",
        ip_version=4,
        policy_version="2026-08-26",
        dedupe_key="example-dedupe",
        expires_at=now + timedelta(days=30),
    )
    assert observation.eligibility_status == NetworkEligibilityStatus.pending.value


def test_database_contracts_enforce_domain_invariants() -> None:
    observation_constraints = {
        constraint.name for constraint in NetworkObservation.__table__.constraints
    }
    identification_constraints = {
        constraint.name for constraint in CompanyIdentification.__table__.constraints
    }
    usage_constraints = {constraint.name for constraint in ProviderUsage.__table__.constraints}

    assert "ck_network_observation_ip_version" in observation_constraints
    assert "ck_network_observation_expiry" in observation_constraints
    assert "ck_company_identification_confidence" in identification_constraints
    assert "ck_company_identification_status" in identification_constraints
    assert "ck_provider_usage_estimated_cost" in usage_constraints


def test_domain_status_contracts_are_explicit() -> None:
    assert {item.value for item in IdentificationStatus} == {
        "shadow",
        "candidate",
        "confirmed",
        "rejected",
        "expired",
        "conflict",
    }
    assert {item.value for item in IdentificationReviewDecision} == {
        "confirm",
        "reject",
        "correct",
    }


@pytest.mark.asyncio
async def test_mock_provider_obeys_stable_adapter_contract() -> None:
    candidate = CompanyCandidate(
        company_name="Acme Industrial",
        domain="acme.example",
        candidate_key="acme.example",
        confidence=0.97,
        match_method="fixture",
        evidence={"source": "contract-test"},
    )
    provider = MockCompanyIdentificationProvider({"203.0.113.10": (candidate,)})
    context = CompanyLookupContext(
        tenant_id=uuid.uuid4(),
        observation_id=uuid.uuid4(),
        ip_address="203.0.113.10",
    )
    assert "203.0.113.10" not in repr(context)

    result = await provider.identify_company(context)

    assert result.provider == "mock"
    assert result.request_id == f"mock-{context.observation_id}"
    assert result.candidates == (candidate,)
    assert result.units == 0
    assert result.metadata == {"mock": True}
    assert await provider.healthcheck() is True


def test_production_registry_cannot_resolve_mock_provider(monkeypatch) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "PDL_DATA_USE_APPROVED", False)
    monkeypatch.setattr(settings, "PDL_API_KEY", "")
    monkeypatch.setattr(settings, "PDL_IP_ENRICH_ESTIMATED_COST", 0)

    assert "mock" not in available_provider_names()
    with pytest.raises(
        UnsupportedCompanyIdentificationProvider,
        match="is not configured",
    ):
        get_company_identification_provider("mock")


def test_candidate_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        CompanyCandidate(
            company_name="Bad Candidate",
            candidate_key="bad.example",
            confidence=1.5,
            match_method="fixture",
        )


def test_company_identification_job_payload_never_contains_ip() -> None:
    session = _CollectingSession()
    tenant_id = uuid.uuid4()
    observation_id = uuid.uuid4()

    job = enqueue_company_identification_job(
        session,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        network_observation_id=observation_id,
    )

    assert session.added == [job]
    assert job.job_type == "company_identify"
    assert json.loads(job.payload_json) == {"network_observation_id": str(observation_id)}
    assert "ip" not in job.payload_json.lower()
    assert job.idempotency_key == f"company-identify:{tenant_id}:{observation_id}"


def test_company_candidate_model_keeps_provider_evidence() -> None:
    now = utcnow_naive()
    row = CompanyIdentification(
        tenant_id=uuid.uuid4(),
        visitor_id=uuid.uuid4(),
        network_observation_id=uuid.uuid4(),
        company_name="Acme Industrial",
        domain="acme.example",
        provider="mock",
        candidate_key="acme.example",
        confidence=0.91,
        confidence_band="high",
        evidence_json={"network": "fixture"},
        match_method="fixture",
        expires_at=now + timedelta(days=30),
    )
    assert row.status == IdentificationStatus.shadow.value
    assert row.evidence_json == {"network": "fixture"}
