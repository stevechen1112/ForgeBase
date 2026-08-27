"""Batch-8 safe-retirement observation and approval gate tests."""

import json
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.core.security import create_access_token, get_password_hash
from app.models.operational_job import OperationalJob
from app.models.retirement import RetirementUsageEvent
from app.models.tenant import Tenant
from app.models.user import User
from app.services import agentOS, operational_outbox
from app.services.capability_access import resolve_tenant_features
from tests.conftest import _make_engine, requires_db


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_superuser(factory) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    async with factory() as db:
        db.add(
            User(
                id=user_id,
                tenant_id=None,
                email=f"retirement-{uuid.uuid4().hex[:8]}@example.com",
                full_name="Retirement Reviewer",
                hashed_password=get_password_hash("testpass"),
                role="admin",
                is_active=True,
                is_superuser=True,
            )
        )
        await db.commit()
    return user_id, create_access_token(str(user_id))


def test_retirement_candidates_are_not_enabled_by_phase2_preset() -> None:
    tenant = Tenant(name="Observation", slug="observation")
    features = resolve_tenant_features(tenant)
    assert features["ml_scoring"] is False
    assert features["ai_relation_recommendations"] is False
    assert features["automation_runs"] is False


def test_usage_event_contract_contains_no_request_payload_or_pii_fields() -> None:
    columns = set(RetirementUsageEvent.__table__.columns.keys())
    assert columns == {
        "id",
        "candidate_key",
        "tenant_id",
        "event_name",
        "source",
        "occurred_at",
    }


@pytest.mark.asyncio
async def test_tenantless_agentos_job_cannot_bypass_locked_feature(monkeypatch) -> None:
    trigger = AsyncMock()
    monkeypatch.setattr(agentOS, "trigger_agentOS_rfq", trigger)
    job = OperationalJob(
        job_type="rfq_agentos",
        payload_json=json.dumps({"rfq_id": str(uuid.uuid4()), "tenant_id": None}),
        idempotency_key=f"retired-agentos-{uuid.uuid4()}",
    )
    await operational_outbox._execute(job)
    trigger.assert_not_awaited()


@requires_db
@pytest.mark.asyncio
async def test_retirement_report_records_use_and_blocks_early_removal(
    http_client,
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant, _ = two_tenants
    engine, factory = _make_engine()
    platform_id, platform_token = await _create_superuser(factory)
    try:
        tenant_token = await admin_token_for_tenant(tenant.id)
        platform_headers = _auth(platform_token)
        tenant_headers = _auth(tenant_token)

        blocked_ml = await http_client.get(
            "/api/v1/tracking/ml/status", headers=tenant_headers
        )
        assert blocked_ml.status_code == 403

        async with factory() as db:
            stored = await db.get(Tenant, tenant.id)
            stored.feature_overrides = {
                **(stored.feature_overrides or {}),
                "ml_scoring": True,
            }
            db.add(stored)
            await db.commit()

        used_ml = await http_client.get(
            "/api/v1/tracking/ml/status", headers=tenant_headers
        )
        assert used_ml.status_code == 200, used_ml.text

        report = await http_client.get(
            "/api/v1/admin/retirement-audit", headers=platform_headers
        )
        assert report.status_code == 200, report.text
        candidates = {
            item["candidate_key"]: item for item in report.json()["candidates"]
        }
        assert {
            "agentos_runtime",
            "ml_scoring_runtime",
            "notification_telegram",
            "notification_line",
            "relation_recommender",
            "copilot_floating_widget",
            "legacy_ip_resolver",
        } <= set(candidates)
        assert candidates["copilot_floating_widget"]["status"] == "removed"
        assert candidates["legacy_ip_resolver"]["status"] == "removed"
        assert candidates["ml_scoring_runtime"]["recent_usage_count"] >= 1
        assert "usage_detected" in candidates["ml_scoring_runtime"]["blockers"]
        assert candidates["ml_scoring_runtime"]["removal_ready"] is False

        too_early = await http_client.put(
            "/api/v1/admin/retirement-audit/ml_scoring_runtime/decision",
            headers=platform_headers,
            json={
                "status": "approved_removal",
                "reason": "Attempted before the mandatory evidence window was complete.",
            },
        )
        assert too_early.status_code == 409
        assert "observation_window_incomplete" in too_early.text

        relation_blocked = await http_client.get(
            f"/api/v1/content/products/{uuid.uuid4()}/recommend-relations",
            headers=tenant_headers,
        )
        assert relation_blocked.status_code == 403
    finally:
        async with factory() as db:
            await db.exec(
                text("DELETE FROM platform_audit_logs WHERE actor_user_id = :id"),
                params={"id": str(platform_id)},
            )
            await db.exec(
                text("DELETE FROM users WHERE id = :id"),
                params={"id": str(platform_id)},
            )
            await db.commit()
        await engine.dispose()
