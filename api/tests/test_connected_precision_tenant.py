"""Delivery-contract tests for the second connected website tenant."""
import json

import pytest
from httpx import AsyncClient

from app.models.site_build import SiteBuild
from app.models.site_profile import SiteProfile
from app.models.user import User
from app.services.site_provisioning import SITE_TEMPLATES, evaluate_site_readiness
from app.services.dynamic_cta import select_dynamic_cta
from app.services.chat_service import _tenant_chat_copy
from tests.conftest import requires_db


def test_precision_template_has_explicit_cms_adapter() -> None:
    template = SITE_TEMPLATES["precision-machining"]
    assert template["cms_connected"] is True
    assert template["demo_url"].startswith("https://axisform.")


def test_dynamic_cta_personalization_respects_requested_locale() -> None:
    ctas = [{"action_type": "contact"}]
    english = select_dynamic_cta("cold", 0, ctas, locale="en")
    chinese = select_dynamic_cta("cold", 0, ctas, locale="zh-TW")
    assert english["personalization"]["headline_prefix"] == "Ready when you have a requirement"
    assert chinese["personalization"]["headline_prefix"] == "有需求時，歡迎進一步聯絡"


def test_tenant_chat_copy_replaces_industry_inappropriate_defaults() -> None:
    site_copy = json.dumps({
        "chat": {
            "greeting": {"en": "Review a machining requirement."},
            "suggestions": {"en": ["Which tolerance is shown?", "What inspection is described?"]},
        }
    })
    greeting, suggestions = _tenant_chat_copy(site_copy, "en")
    assert greeting == "Review a machining requirement."
    assert suggestions == ["Which tolerance is shown?", "What inspection is described?"]
    assert "OEM" not in " ".join(suggestions)


@requires_db
@pytest.mark.asyncio
async def test_tenant_profile_updates_are_isolated_and_delivery_copy_is_restricted(
    http_client: AsyncClient,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    updated = await http_client.put(
        "/api/v1/site-profile",
        json={"brand_name": "Tenant Alpha Precision"},
        headers={"Authorization": f"Bearer {token_a}", "X-Tenant-ID": str(tenant_a.id)},
    )
    assert updated.status_code == 200, updated.text

    restricted = await http_client.put(
        "/api/v1/site-profile",
        json={"site_copy_json": json.dumps({"common": {"brandName": "Unsafe overwrite"}})},
        headers={"Authorization": f"Bearer {token_a}", "X-Tenant-ID": str(tenant_a.id)},
    )
    assert restricted.status_code == 403

    profile_b = await http_client.get(
        "/api/v1/site-profile",
        headers={"X-Tenant-ID": str(tenant_b.id)},
    )
    assert profile_b.status_code == 200, profile_b.text
    assert profile_b.json()["brand_name"] != "Tenant Alpha Precision"
    assert profile_b.json().get("site_copy_json") != json.dumps({"common": {"brandName": "Unsafe overwrite"}})


@requires_db
@pytest.mark.asyncio
async def test_precision_build_readiness_requires_matching_host_and_owner(two_tenants) -> None:
    from tests.conftest import _make_engine

    tenant, _ = two_tenants
    engine, factory = _make_engine()
    async with factory() as session:
        profile = SiteProfile(
            tenant_id=tenant.id,
            brand_name="AxisForm Test",
            contact_email="test@example.com",
            site_url="https://precision.example.test",
            theme_key="precision",
            layout_key="precision",
        )
        owner = User(
            tenant_id=tenant.id,
            email=f"owner-{tenant.id}@example.test",
            full_name="Test Owner",
            hashed_password="not-used",  # pragma: allowlist secret -- test fixture
            role="owner",
            is_active=True,
        )
        build = SiteBuild(
            tenant_id=tenant.id,
            template_key="precision-machining",
            primary_domain="precision.example.test",
            locales_json='["en"]',
            cms_connected=True,
        )
        session.add(profile)
        session.add(owner)
        session.add(build)
        await session.commit()
        readiness = await evaluate_site_readiness(session, build)

    await engine.dispose()
    assert readiness["ready"] is True
    assert readiness["blockers"] == []
