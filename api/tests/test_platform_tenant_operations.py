"""Platform-operator workflows for multi-tenant website delivery."""

import uuid

import pytest
from app.core.security import create_access_token, get_password_hash
from app.models.user import User
from sqlalchemy import text

from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_platform_superuser() -> tuple[uuid.UUID, str]:
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            user = User(
                tenant_id=None,
                email=f"platform-{uuid.uuid4().hex[:10]}@example.com",
                full_name="Platform Operator",
                hashed_password=get_password_hash("testpass"),
                role="admin",
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user.id, create_access_token(str(user.id))
    finally:
        await engine.dispose()


async def _delete_platform_superuser(user_id: uuid.UUID) -> None:
    engine, factory = _make_engine()
    try:
        async with factory() as session:
            await session.exec(
                text("UPDATE site_builds SET delivery_owner_id = NULL WHERE delivery_owner_id = :user_id"),
                params={"user_id": str(user_id)},
            )
            await session.exec(
                text("DELETE FROM platform_audit_logs WHERE actor_user_id = :user_id"),
                params={"user_id": str(user_id)},
            )
            await session.exec(
                text("DELETE FROM tenant_provisioning_runs WHERE actor_user_id = :user_id"),
                params={"user_id": str(user_id)},
            )
            await session.exec(
                text("DELETE FROM users WHERE id = :user_id"),
                params={"user_id": str(user_id)},
            )
            await session.commit()
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_platform_operator_can_manage_delivery_and_audit_actions(
    http_client,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant_a, _ = two_tenants
    platform_user_id, platform_token = await _create_platform_superuser()
    secondary_operator_id: uuid.UUID | None = None
    tenant_admin_token = await admin_token_for_tenant(tenant_a.id)
    try:
        denied = await http_client.get("/api/v1/admin/tenants", headers=_auth(tenant_admin_token))
        assert denied.status_code == 403

        created_operator = await http_client.post(
            "/api/v1/admin/platform-users",
            json={
                "email": f"delivery-{uuid.uuid4().hex[:10]}@example.com",
                "full_name": "Delivery Operator",
                "temporary_password": "temporary-password-123",  # pragma: allowlist secret -- test fixture
            },
            headers=_auth(platform_token),
        )
        assert created_operator.status_code == 201, created_operator.text
        secondary_operator_id = uuid.UUID(created_operator.json()["id"])
        suspended_operator = await http_client.patch(
            f"/api/v1/admin/platform-users/{secondary_operator_id}",
            json={"is_active": False},
            headers=_auth(platform_token),
        )
        assert suspended_operator.status_code == 200, suspended_operator.text
        assert suspended_operator.json()["is_active"] is False

        initial = await http_client.get(
            "/api/v1/admin/tenants?needs_attention=true",
            headers=_auth(platform_token),
        )
        assert initial.status_code == 200, initial.text
        tenant_row = next(item for item in initial.json() if item["id"] == str(tenant_a.id))
        assert "site_build_missing" in tenant_row["attention_reasons"]

        created = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-build",
            json={
                "template_key": "handtool-company",
                "primary_domain": f"{tenant_a.slug}.example.test",
                "locales": ["en", "zh-TW", "ja", "fr", "ru"],
            },
            headers=_auth(platform_token),
        )
        assert created.status_code == 201, created.text
        assert created.json()["status"] == "draft"
        assert created.json()["locales"] == ["en", "zh-TW", "ja", "fr", "ru"]

        site_profile = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-profile",
            headers=_auth(platform_token),
        )
        assert site_profile.status_code == 200, site_profile.text

        profile_updated = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-profile",
            json={
                "theme_key": "forest",
                "header_nav_json": '[{"label":"Products","href":"/products"}]',
            },
            headers=_auth(platform_token),
        )
        assert profile_updated.status_code == 200, profile_updated.text
        assert profile_updated.json()["theme_key"] == "forest"

        invalid_profile_json = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-profile",
            json={"header_nav_json": "{"},
            headers=_auth(platform_token),
        )
        assert invalid_profile_json.status_code == 422

        tenant_cannot_change_delivery_settings = await http_client.put(
            "/api/v1/site-profile",
            json={"theme_key": "industrial"},
            headers=_auth(tenant_admin_token),
        )
        assert tenant_cannot_change_delivery_settings.status_code == 403

        connected = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-build",
            json={"cms_connected": True},
            headers=_auth(platform_token),
        )
        assert connected.status_code == 200, connected.text
        assert connected.json()["cms_connected"] is True

        same_template_update = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-build",
            json={
                "template_key": "handtool-company",
                "primary_domain": f"www.{tenant_a.slug}.example.test",
            },
            headers=_auth(platform_token),
        )
        assert same_template_update.status_code == 200, same_template_update.text
        assert same_template_update.json()["cms_connected"] is True

        validated = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-build/validate",
            json={},
            headers=_auth(platform_token),
        )
        assert validated.status_code == 200, validated.text
        assert validated.json()["status"] == "blocked"
        assert validated.json()["readiness"]["ready"] is False

        # Internal delivery coordination must not invalidate a technical
        # readiness result.  It is deliberately a separate workflow layer.
        delivery_updated = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-build",
            json={
                "delivery_stage": "qa",
                "delivery_owner_id": str(platform_user_id),
                "target_launch_at": "2026-09-01T12:00:00.000Z",
                "handoff_at": "2026-09-02T12:00:00.000Z",
                "acceptance_status": "requested",
                "internal_note": "Waiting for the internal QA checklist.",
            },
            headers=_auth(platform_token),
        )
        assert delivery_updated.status_code == 200, delivery_updated.text
        assert delivery_updated.json()["status"] == "blocked"
        assert delivery_updated.json()["delivery_stage"] == "qa"
        assert delivery_updated.json()["delivery_owner_id"] == str(platform_user_id)
        assert delivery_updated.json()["target_launch_at"].startswith("2026-09-01")
        assert delivery_updated.json()["handoff_at"].startswith("2026-09-02")
        assert delivery_updated.json()["acceptance_status"] == "requested"

        workspace = await http_client.get("/api/v1/admin/workspace", headers=_auth(platform_token))
        assert workspace.status_code == 200, workspace.text
        assert {"adoption_review", "delivery_open", "rfq_attention", "failed_jobs"}.issubset(workspace.json()["counts"])

        delivery_board = await http_client.get("/api/v1/admin/delivery-board?stage=qa", headers=_auth(platform_token))
        assert delivery_board.status_code == 200, delivery_board.text
        board_item = next(item for item in delivery_board.json() if item["tenant_id"] == str(tenant_a.id))
        assert board_item["delivery_stage"] == "qa"
        assert board_item["technical_status"] == "blocked"

        for endpoint in ("/api/v1/admin/rfqs", "/api/v1/admin/resources/status", "/api/v1/admin/usage", "/api/v1/admin/audit-log"):
            response = await http_client.get(endpoint, headers=_auth(platform_token))
            assert response.status_code == 200, response.text

        blocked_publish = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_a.id}/site-build/publish",
            json={},
            headers=_auth(platform_token),
        )
        assert blocked_publish.status_code == 409

        suspended = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_a.id}",
            json={"is_active": False},
            headers=_auth(platform_token),
        )
        assert suspended.status_code == 200, suspended.text
        assert suspended.json()["is_active"] is False

        audit = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_a.id}/audit-log",
            headers=_auth(platform_token),
        )
        assert audit.status_code == 200, audit.text
        actions = {item["action"] for item in audit.json()}
        assert {
            "site_build.created",
            "site_build.updated",
            "site_build.validated",
            "site_build.publish_blocked",
            "site_profile.updated",
            "tenant.updated",
        }.issubset(actions)

        dashboard = await http_client.get("/api/v1/admin/dashboard", headers=_auth(platform_token))
        assert dashboard.status_code == 200, dashboard.text
        payload = dashboard.json()
        assert "tenants_needing_attention" in payload
        assert "attention_tenants" in payload
        assert "rfqs_30d" in payload
    finally:
        if secondary_operator_id:
            await _delete_platform_superuser(secondary_operator_id)
        await _delete_platform_superuser(platform_user_id)


@requires_db
@pytest.mark.asyncio
async def test_tenant_delivery_factory_is_preflighted_atomic_and_replay_safe(
    http_client,
) -> None:
    platform_user_id, platform_token = await _create_platform_superuser()
    suffix = uuid.uuid4().hex[:10]
    slug = f"delivery-{suffix}"
    tenant_id: uuid.UUID | None = None
    payload = {
        "name": f"Delivery Factory {suffix}",
        "slug": slug,
        "owner_email": f"owner-{suffix}@example.com",
        "owner_full_name": "Delivery Owner",
        "temporary_password": "factory-test-password-123",  # pragma: allowlist secret -- test fixture
        "template_key": "handtool-company",
        "brand_name": f"Factory {suffix}",
        "logo_mark": "DF",
        "contact_email": f"sales-{suffix}@example.com",
        "site_url": f"https://{slug}.example.test",
        "primary_domain": f"{slug}.example.test",
        "default_locale": "zh-TW",
        "locales": ["zh-TW", "en", "ja", "fr", "ru"],
        "theme_key": "cobalt",
        "layout_key": "classic",
    }
    request_key = f"tenant-delivery-{suffix}"
    headers = {**_auth(platform_token), "Idempotency-Key": request_key}
    try:
        static_payload = {**payload, "template_key": "industrial-machinery"}
        static_preflight = await http_client.post(
            "/api/v1/admin/tenant-provisioning/preflight",
            json=static_payload,
            headers=_auth(platform_token),
        )
        assert static_preflight.status_code == 200, static_preflight.text
        assert static_preflight.json()["ready"] is False
        assert "template_publishable" in static_preflight.json()["blockers"]

        malformed_preflight = await http_client.post(
            "/api/v1/admin/tenant-provisioning/preflight",
            json={
                **payload,
                "site_url": "https://[invalid",
                "primary_domain": "invalid.example.test",
            },
            headers=_auth(platform_token),
        )
        assert malformed_preflight.status_code == 200, malformed_preflight.text
        assert malformed_preflight.json()["ready"] is False
        assert "https_site_url" in malformed_preflight.json()["blockers"]

        preflight = await http_client.post(
            "/api/v1/admin/tenant-provisioning/preflight",
            json=payload,
            headers=_auth(platform_token),
        )
        assert preflight.status_code == 200, preflight.text
        assert preflight.json()["ready"] is True

        missing_key = await http_client.post(
            "/api/v1/admin/tenants",
            json=payload,
            headers=_auth(platform_token),
        )
        assert missing_key.status_code == 422

        created = await http_client.post(
            "/api/v1/admin/tenants", json=payload, headers=headers
        )
        assert created.status_code == 201, created.text
        created_body = created.json()
        tenant_id = uuid.UUID(created_body["tenant_id"])
        assert created_body["status"] == "blocked"
        assert created_body["delivery_stage"] == "intake"
        assert created_body["readiness"]["blockers"] == ["cms_adapter_connected"]
        assert created_body["next_actions"] == [
            "confirm_cms_adapter",
            "validate_site",
            "publish_site",
        ]

        replay = await http_client.post(
            "/api/v1/admin/tenants",
            json={**payload, "temporary_password": "different-retry-password-456"},  # pragma: allowlist secret -- replay must ignore write-only credentials
            headers=headers,
        )
        assert replay.status_code == 201, replay.text
        assert replay.headers["Idempotent-Replayed"] == "true"
        assert replay.json() == created_body

        manifest = await http_client.get(
            f"/api/v1/admin/tenants/{tenant_id}/provisioning-manifest",
            headers=_auth(platform_token),
        )
        assert manifest.status_code == 200, manifest.text
        assert manifest.json()["run_id"] == created_body["provisioning_run_id"]
        assert manifest.json()["manifest"] == created_body

        changed_payload = {**payload, "brand_name": "Different request"}
        key_reuse = await http_client.post(
            "/api/v1/admin/tenants", json=changed_payload, headers=headers
        )
        assert key_reuse.status_code == 409

        premature_live = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_id}/site-build",
            json={"delivery_stage": "live"},
            headers=_auth(platform_token),
        )
        assert premature_live.status_code == 409
        assert premature_live.json()["error"]["error"] == "delivery_stage_not_ready"

        connected = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_id}/site-build",
            json={"cms_connected": True},
            headers=_auth(platform_token),
        )
        assert connected.status_code == 200, connected.text
        validated = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/site-build/validate",
            json={},
            headers=_auth(platform_token),
        )
        assert validated.status_code == 200, validated.text
        assert validated.json()["status"] == "ready"
        published = await http_client.post(
            f"/api/v1/admin/tenants/{tenant_id}/site-build/publish",
            json={},
            headers=_auth(platform_token),
        )
        assert published.status_code == 200, published.text

        live_without_handoff = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_id}/site-build",
            json={"delivery_stage": "live"},
            headers=_auth(platform_token),
        )
        assert live_without_handoff.status_code == 409
        assert {
            "delivery_owner_assigned",
            "handoff_recorded",
            "acceptance_complete",
        }.issubset(live_without_handoff.json()["error"]["blockers"])

        completed_delivery = await http_client.put(
            f"/api/v1/admin/tenants/{tenant_id}/site-build",
            json={
                "delivery_stage": "live",
                "delivery_owner_id": str(platform_user_id),
                "handoff_at": "2026-09-02T12:00:00.000Z",
                "acceptance_status": "accepted",
            },
            headers=_auth(platform_token),
        )
        assert completed_delivery.status_code == 200, completed_delivery.text
        assert completed_delivery.json()["delivery_stage"] == "live"

        immutable_replay = await http_client.post(
            "/api/v1/admin/tenants", json=payload, headers=headers
        )
        assert immutable_replay.status_code == 201
        assert immutable_replay.json() == created_body

        engine, factory = _make_engine()
        try:
            async with factory() as session:
                counts = (
                    await session.exec(
                        text(
                            """
                            SELECT
                              (SELECT COUNT(*) FROM tenants WHERE id = :tenant_id) AS tenants,
                              (SELECT COUNT(*) FROM users WHERE tenant_id = :tenant_id) AS owners,
                              (SELECT COUNT(*) FROM site_profiles WHERE tenant_id = :tenant_id) AS profiles,
                              (SELECT COUNT(*) FROM site_builds WHERE tenant_id = :tenant_id) AS builds,
                              (SELECT COUNT(*) FROM tenant_provisioning_runs WHERE tenant_id = :tenant_id) AS runs
                            """
                        ),
                        params={"tenant_id": str(tenant_id)},
                    )
                ).mappings().one()
                assert dict(counts) == {
                    "tenants": 1,
                    "owners": 1,
                    "profiles": 1,
                    "builds": 1,
                    "runs": 1,
                }
                stored = (
                    await session.exec(
                        text(
                            "SELECT response_json, request_fingerprint FROM tenant_provisioning_runs "
                            "WHERE tenant_id = :tenant_id"
                        ),
                        params={"tenant_id": str(tenant_id)},
                    )
                ).mappings().one()
                assert payload["temporary_password"] not in stored["response_json"]
                assert len(stored["request_fingerprint"]) == 64
        finally:
            await engine.dispose()
    finally:
        if tenant_id:
            engine, factory = _make_engine()
            try:
                async with factory() as session:
                    params = {"tenant_id": str(tenant_id)}
                    await session.exec(text("DELETE FROM platform_audit_logs WHERE tenant_id = :tenant_id"), params=params)
                    await session.exec(text("DELETE FROM tenant_provisioning_runs WHERE tenant_id = :tenant_id"), params=params)
                    await session.exec(text("DELETE FROM site_builds WHERE tenant_id = :tenant_id"), params=params)
                    await session.exec(text("DELETE FROM site_profiles WHERE tenant_id = :tenant_id"), params=params)
                    await session.exec(text("DELETE FROM users WHERE tenant_id = :tenant_id"), params=params)
                    await session.exec(text("DELETE FROM tenants WHERE id = :tenant_id"), params=params)
                    await session.commit()
            finally:
                await engine.dispose()
        await _delete_platform_superuser(platform_user_id)
