"""Single-product capability defaults and governance overrides."""

import uuid

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.notification_log import NotificationLog
from app.models.tenant import Tenant
from app.models.user import User
from app.services.capability_access import resolve_tenant_features, tenant_has_feature
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_single_product_defaults_and_governance_overrides() -> None:
    tenant = Tenant(name="Pilot", slug="pilot")
    defaults = resolve_tenant_features(tenant)
    for feature in (
        "outcomes_dashboard", "full_tracking", "intent_scoring", "ai_advisor",
        "chat_handoff", "audience_segments", "nurture_email", "rfq_workspace",
        "notifications", "follow_up_reminders",
    ):
        assert defaults[feature] is True

    tenant.feature_overrides = {"nurture_email": False, "advanced_content": False}
    assert tenant_has_feature(tenant, "nurture_email") is False
    assert tenant_has_feature(tenant, "dynamic_cta") is True

    # External dependencies cannot be enabled by a crafted override.
    tenant.feature_overrides = {"company_identification": True, "automation_runs": True}
    resolved = resolve_tenant_features(tenant)
    assert resolved["company_identification"] is False
    assert resolved["automation_runs"] is False


@requires_db
@pytest.mark.asyncio
async def test_platform_operator_can_govern_capabilities_and_api_enforces_override(
    http_client,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    platform_id = uuid.uuid4()
    try:
        async with factory() as session:
            operator = User(
                id=platform_id,
                tenant_id=None,
                email=f"feature-{uuid.uuid4().hex[:8]}@example.com",
                full_name="Feature Operator",
                hashed_password=get_password_hash("testpass"),
                role="admin",
                is_active=True,
                is_superuser=True,
            )
            session.add(operator)
            await session.commit()

        platform_token = create_access_token(str(platform_id))
        tenant_token = await admin_token_for_tenant(tenant.id)
        async with factory() as session:
            session.add_all([
                NotificationLog(tenant_id=tenant.id, channel="in_app", event_type="new_rfq", status="sent"),
                NotificationLog(tenant_id=tenant.id, channel="in_app", event_type="hot_visitor", status="sent"),
                NotificationLog(tenant_id=tenant.id, channel="in_app", event_type="chat_handoff", status="sent"),
            ])
            await session.commit()

        catalog = await http_client.get("/api/v1/admin/feature-catalog", headers=_auth(platform_token))
        assert catalog.status_code == 200, catalog.text
        assert any(item["key"] == "company_identification" and not item["configurable"] for item in catalog.json()["features"])

        for path in (
            "/api/v1/tracking/segments", "/api/v1/tracking/outcomes",
            "/api/v1/tracking/analytics/funnel", "/api/v1/tracking/visitors",
        ):
            response = await http_client.get(path, headers=_auth(tenant_token))
            assert response.status_code == 200, response.text

        enabled = await http_client.put(
            f"/api/v1/admin/tenants/{tenant.id}",
            json={"feature_overrides": {"nurture_email": False, "audience_segments": False}},
            headers=_auth(platform_token),
        )
        assert enabled.status_code == 200, enabled.text
        assert enabled.status_code == 200

        current = await http_client.get("/api/v1/capabilities/access", headers=_auth(tenant_token))
        assert current.status_code == 200, current.text
        assert current.json()["product"] == "forgebase"
        assert current.json()["features"]["audience_segments"] is False
        assert current.json()["features"]["nurture_email"] is False

        disabled_segments = await http_client.get("/api/v1/tracking/segments", headers=_auth(tenant_token))
        assert disabled_segments.status_code == 403
        notifications = await http_client.get("/api/v1/copilot/notifications", headers=_auth(tenant_token))
        assert notifications.status_code == 200, notifications.text
        assert {item["event_type"] for item in notifications.json()["data"]} == {
            "new_rfq", "hot_visitor", "chat_handoff",
        }

        disabled_nurture = await http_client.get("/api/v1/nurture/sequences", headers=_auth(tenant_token))
        assert disabled_nurture.status_code == 403
    finally:
        async with factory() as session:
            from sqlalchemy import text

            await session.exec(
                text("DELETE FROM platform_audit_logs WHERE actor_user_id = :id"),
                params={"id": str(platform_id)},
            )
            await session.exec(
                text("DELETE FROM users WHERE id = :id"),
                params={"id": str(platform_id)},
            )
            await session.commit()
        await engine.dispose()
