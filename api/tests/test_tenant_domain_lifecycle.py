import uuid

import pytest
from app.services.domain_verification import DNSLookupError, DomainDNSObservation
from sqlalchemy import text

from tests.conftest import _make_engine, requires_db
from tests.test_platform_tenant_operations import (
    _auth,
    _create_platform_superuser,
    _delete_platform_superuser,
)


@requires_db
@pytest.mark.asyncio
async def test_custom_domain_never_bypasses_dns_and_falls_back_safely(
    http_client, monkeypatch
) -> None:
    operator_id, token = await _create_platform_superuser()
    suffix = uuid.uuid4().hex[:10]
    slug = f"domain-{suffix}"
    custom_host = f"www.{slug}.example.test"
    tenant_id: uuid.UUID | None = None
    payload = {
        "name": f"Domain Lifecycle {suffix}",
        "slug": slug,
        "owner_email": f"owner-{suffix}@example.com",
        "owner_full_name": "Domain Owner",
        "temporary_password": "domain-lifecycle-test-password",  # pragma: allowlist secret -- test fixture
        "template_key": "handtool-company",
        "brand_name": f"Domain {suffix}",
        "logo_mark": "DL",
        "contact_email": f"sales-{suffix}@example.com",
        "site_url": f"https://{custom_host}",
        "primary_domain": custom_host,
        "default_locale": "en",
        "locales": ["en"],
    }
    try:
        created = await http_client.post(
            "/api/v1/admin/tenants",
            json=payload,
            headers={
                **_auth(token),
                "Idempotency-Key": f"domain-lifecycle-{suffix}",
            },
        )
        assert created.status_code == 201, created.text
        tenant_id = uuid.UUID(created.json()["tenant_id"])
        managed_host = f"{slug}.forgebase.com"
        assert created.json()["site_url"] == f"https://{managed_host}"
        assert created.json()["requested_custom_domain"] == custom_host
        assert created.json()["custom_domain_status"] == "pending"

        renamed_label = f"axisform-{suffix}"
        renamed = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_id}/domains/managed",
            headers=_auth(token),
            json={"label": renamed_label},
        )
        assert renamed.status_code == 200, renamed.text
        managed_host = f"{renamed_label}.forgebase.com"
        assert renamed.json()["hostname"] == managed_host
        assert renamed.json()["is_canonical"] is True

        renamed_detail = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}", headers=_auth(token)
        )
        assert renamed_detail.json()["primary_domain"] == managed_host

        domains = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}/domains", headers=_auth(token)
        )
        assert domains.status_code == 200, domains.text
        by_host = {item["hostname"]: item for item in domains.json()}
        assert set(by_host) == {managed_host, custom_host}
        assert by_host[managed_host]["is_canonical"] is True
        assert by_host[custom_host]["status"] == "pending"
        custom_id = by_host[custom_host]["id"]
        assert by_host[custom_host]["verification"]["record_name"] == (
            f"_forgebase-verification.{custom_host}"
        )
        tenant_attention = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}", headers=_auth(token)
        )
        assert "custom_domain_pending" in tenant_attention.json()["attention_reasons"]
        workspace = await http_client.get(
            "/api/v1/admin/workspace", headers=_auth(token)
        )
        assert workspace.status_code == 200
        assert workspace.json()["counts"]["domain_attention"] >= 1
        assert any(
            item["kind"] == "tenant_domain" and item["tenant_id"] == str(tenant_id)
            for item in workspace.json()["work_items"]
        )

        async def incomplete_dns(*_args, **_kwargs):
            return DomainDNSObservation(
                verification_hostname=f"_forgebase-verification.{custom_host}",
                expected_txt_value="expected",
                expected_routing_target="edge.forgebase.com",
                txt_values=[],
                cname_targets=["edge.forgebase.com"],
                domain_addresses=[],
                target_addresses=[],
                ownership_verified=False,
                routing_verified=True,
            )

        monkeypatch.setattr(
            "app.api.v1.endpoints.tenant_domains_admin.inspect_custom_domain_dns",
            incomplete_dns,
        )
        blocked = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/domains/{custom_id}/activate",
            headers=_auth(token),
        )
        assert blocked.status_code == 409
        assert blocked.json()["error"]["error"] == "domain_dns_not_ready"

        async def ready_dns(*_args, **_kwargs):
            return DomainDNSObservation(
                verification_hostname=f"_forgebase-verification.{custom_host}",
                expected_txt_value="expected",
                expected_routing_target="edge.forgebase.com",
                txt_values=["expected"],
                cname_targets=["edge.forgebase.com"],
                domain_addresses=[],
                target_addresses=[],
                ownership_verified=True,
                routing_verified=True,
            )

        monkeypatch.setattr(
            "app.api.v1.endpoints.tenant_domains_admin.inspect_custom_domain_dns",
            ready_dns,
        )
        activated = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/domains/{custom_id}/activate",
            headers=_auth(token),
        )
        assert activated.status_code == 200, activated.text
        assert activated.json()["status"] == "active"
        assert activated.json()["is_canonical"] is True
        activated_attention = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}", headers=_auth(token)
        )
        assert "custom_domain_pending" not in activated_attention.json()["attention_reasons"]

        alias_route = await http_client.get(
            "/api/v1/site-domain-routing", headers={"Host": managed_host}
        )
        assert alias_route.status_code == 200
        assert alias_route.json() == {
            "hostname": managed_host,
            "canonical_hostname": custom_host,
            "redirect_required": True,
        }
        build = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}/site-build", headers=_auth(token)
        )
        profile = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}/site-profile", headers=_auth(token)
        )
        assert build.json()["primary_domain"] == custom_host
        assert profile.json()["site_url"] == f"https://{custom_host}"

        async def unavailable_dns(*_args, **_kwargs):
            raise DNSLookupError("temporary resolver outage")

        monkeypatch.setattr(
            "app.api.v1.endpoints.tenant_domains_admin.inspect_custom_domain_dns",
            unavailable_dns,
        )
        unavailable = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/domains/{custom_id}/verify",
            headers=_auth(token),
        )
        assert unavailable.status_code == 503
        still_live = await http_client.get(
            "/api/v1/site-domain-routing", headers={"Host": managed_host}
        )
        assert still_live.status_code == 200
        assert still_live.json()["canonical_hostname"] == custom_host

        suspended = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/domains/{custom_id}/suspend",
            headers=_auth(token),
        )
        assert suspended.status_code == 200, suspended.text
        assert suspended.json()["status"] == "suspended"
        restored_route = await http_client.get(
            "/api/v1/site-domain-routing", headers={"Host": managed_host}
        )
        assert restored_route.status_code == 200
        assert restored_route.json()["canonical_hostname"] == managed_host
        assert restored_route.json()["redirect_required"] is False
    finally:
        if tenant_id:
            engine, factory = _make_engine()
            try:
                async with factory() as session:
                    params = {"tenant_id": str(tenant_id)}
                    for table in (
                        "platform_audit_logs",
                        "tenant_provisioning_runs",
                        "tenant_domains",
                        "site_builds",
                        "site_profiles",
                        "users",
                        "tenants",
                    ):
                        await session.exec(
                            text(f"DELETE FROM {table} WHERE {'id' if table == 'tenants' else 'tenant_id'} = :tenant_id"),
                            params=params,
                        )
                    await session.commit()
            finally:
                await engine.dispose()
        await _delete_platform_superuser(operator_id)
