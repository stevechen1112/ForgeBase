from decimal import Decimal

import pytest
from app.models.company_identification import GrowthAutomationPolicy
from scripts.manage_company_identification_policy import (
    PROBE_IP,
    parse_tenant_slugs,
    policy_is_ready,
    policy_snapshot,
    probe_real_provider,
)


def test_parse_tenant_slugs_is_explicit_normalized_and_deduplicated() -> None:
    assert parse_tenant_slugs("NorthForge-Tools, axisform-precision,northforge-tools") == [
        "northforge-tools",
        "axisform-precision",
    ]

    with pytest.raises(ValueError):
        parse_tenant_slugs("")
    with pytest.raises(ValueError):
        parse_tenant_slugs("../../all-tenants")


def test_policy_ready_requires_real_provider_shadow_and_positive_gates() -> None:
    policy = GrowthAutomationPolicy(
        company_identification_mode="shadow",
        provider_name="pdl_ip",
        daily_lookup_quota=10,
        daily_provider_cost_limit=Decimal(5),
    )
    assert policy_is_ready(policy) is True

    policy.provider_name = "mock"
    assert policy_is_ready(policy) is False
    policy.provider_name = "pdl_ip"
    policy.daily_lookup_quota = 0
    assert policy_is_ready(policy) is False


def test_policy_snapshot_never_contains_raw_network_or_credentials() -> None:
    snapshot = policy_snapshot(
        GrowthAutomationPolicy(
            company_identification_mode="shadow",
            provider_name="pdl_ip",
        )
    )
    rendered = str(snapshot).lower()
    assert "api_key" not in rendered
    assert "ip_address" not in rendered
    assert snapshot["provider_name"] == "pdl_ip"


@pytest.mark.asyncio
async def test_real_provider_probe_uses_public_fixture_and_minimises_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = {}

    class ProbeResult:
        provider = "pdl_ip"
        candidates = (object(),)
        units = 1

    class ProbeAdapter:
        async def identify_company(self, context):
            captured["ip_address"] = context.ip_address
            captured["tenant_id"] = context.tenant_id
            return ProbeResult()

    monkeypatch.setattr(
        "scripts.manage_company_identification_policy.get_company_identification_provider",
        lambda name: ProbeAdapter(),
    )

    report = await probe_real_provider()

    assert captured["ip_address"] == PROBE_IP == "8.8.8.8"
    assert report == {
        "provider": "pdl_ip",
        "authenticated_request_completed": True,
        "result_class": "matched",
        "candidate_count": 1,
        "units": 1,
    }
    assert "candidate" not in report
    assert "ip_address" not in report
