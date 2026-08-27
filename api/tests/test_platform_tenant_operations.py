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
