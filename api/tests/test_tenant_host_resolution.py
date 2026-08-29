"""Exact-host tenant routing and transitional header boundary tests."""

import pytest
from app.api.v1.deps import (
    _TENANT_HOST_CACHE,
    _TENANT_HOST_CACHE_MAX,
    _cache_tenant_host,
    clear_tenant_host_cache,
)
from app.core.config import settings
from app.models.site_profile import SiteProfile
from app.models.tenant_domain import TenantDomain
from sqlmodel import select

from tests.conftest import _make_engine, requires_db


def test_host_cache_is_bounded_for_untrusted_negative_hosts() -> None:
    clear_tenant_host_cache()
    for index in range(_TENANT_HOST_CACHE_MAX + 20):
        _cache_tenant_host(f"random-{index}.attacker.example", None, float(index))
    assert 0 < len(_TENANT_HOST_CACHE) <= _TENANT_HOST_CACHE_MAX
    assert f"random-{_TENANT_HOST_CACHE_MAX + 19}.attacker.example" in _TENANT_HOST_CACHE
    clear_tenant_host_cache()


@requires_db
@pytest.mark.asyncio
async def test_exact_active_host_wins_and_slug_guessing_is_forbidden(
    http_client,
    two_tenants,
    monkeypatch,
) -> None:
    tenant_a, tenant_b = two_tenants
    host_a = f"alpha-{tenant_a.id.hex[:8]}.example.test"
    host_b = f"beta-{tenant_b.id.hex[:8]}.example.test"
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            session.add(
                SiteProfile(
                    tenant_id=tenant_a.id,
                    brand_name="Exact Host Alpha",
                    logo_mark="EA",
                    contact_email="alpha@example.test",
                    site_url=f"https://{host_a}",
                )
            )
            session.add(
                SiteProfile(
                    tenant_id=tenant_b.id,
                    brand_name="Exact Host Beta",
                    logo_mark="EB",
                    contact_email="beta@example.test",
                    site_url=f"https://{host_b}",
                )
            )
            session.add(
                TenantDomain(
                    tenant_id=tenant_a.id,
                    hostname=host_a,
                    status="active",
                    is_canonical=True,
                    redirect_to_canonical=False,
                )
            )
            session.add(
                TenantDomain(
                    tenant_id=tenant_b.id,
                    hostname=host_b,
                    status="active",
                    is_canonical=True,
                    redirect_to_canonical=False,
                )
            )
            await session.commit()

        clear_tenant_host_cache()
        exact = await http_client.get("/api/v1/site-profile", headers={"Host": host_a.upper()})
        assert exact.status_code == 200, exact.text
        assert exact.json()["brand_name"] == "Exact Host Alpha"

        conflict = await http_client.get(
            "/api/v1/site-profile",
            headers={"Host": host_a, "X-Tenant-ID": str(tenant_b.id)},
        )
        assert conflict.status_code == 400
        assert conflict.json()["error"] == "Tenant host/header mismatch"

        clear_tenant_host_cache()
        guessed = await http_client.get(
            "/api/v1/site-profile",
            headers={"Host": f"{tenant_a.slug}.attacker.example"},
        )
        assert guessed.status_code == 200, guessed.text
        assert guessed.json()["brand_name"] != "Exact Host Alpha"

        clear_tenant_host_cache()
        spoofed_forwarding_header = await http_client.get(
            "/api/v1/site-profile",
            headers={"Host": "public-api.example", "X-Tenant-Host": host_a},
        )
        assert spoofed_forwarding_header.status_code == 200
        assert spoofed_forwarding_header.json()["brand_name"] != "Exact Host Alpha"

        legacy = await http_client.get(
            "/api/v1/site-profile",
            headers={"Host": "public-api.example", "X-Tenant-ID": str(tenant_b.id)},
        )
        assert legacy.status_code == 200, legacy.text
        assert legacy.json()["brand_name"] == "Exact Host Beta"

        monkeypatch.setattr(settings, "PUBLIC_TENANT_HEADER_COMPATIBILITY_ENABLED", False)
        disabled = await http_client.get(
            "/api/v1/site-profile",
            headers={"Host": "public-api.example", "X-Tenant-ID": str(tenant_b.id)},
        )
        assert disabled.status_code == 400
        assert disabled.json()["error"] == "X-Tenant-ID compatibility is disabled"

        # Disabling a lifecycle row must not fall back to SiteProfile.site_url.
        async with factory() as session:
            domain = (
                await session.exec(
                    select(TenantDomain).where(TenantDomain.hostname == host_a)
                )
            ).one()
            assert domain is not None
            domain.status = "suspended"
            session.add(domain)
            await session.commit()
        clear_tenant_host_cache()
        suspended = await http_client.get("/api/v1/site-profile", headers={"Host": host_a})
        assert suspended.status_code == 200
        assert suspended.json()["brand_name"] != "Exact Host Alpha"
    finally:
        clear_tenant_host_cache()
        await engine.dispose()
