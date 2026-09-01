"""Batch-8 safe-retirement observation and approval gate tests."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select, text

from app.core.datetime import utcnow_naive
from app.core.security import create_access_token, decode_token, get_password_hash
from app.models.notification_preference import NotificationPreference
from app.models.retirement import RetirementCandidateObservation, RetirementUsageEvent
from app.models.tenant import Tenant
from app.models.user import User
from app.services.capability_access import resolve_tenant_features
from app.services.notification_router import send_notification
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
    assert features["ai_relation_recommendations"] is False
    assert "automation_runs" not in features


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


@requires_db
@pytest.mark.asyncio
async def test_retired_notification_dispatch_is_fail_closed_and_observed(
    two_tenants,
    admin_token_for_tenant,
) -> None:
    tenant, _ = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    user_id = uuid.UUID(decode_token(token)["sub"])
    engine, factory = _make_engine()
    try:
        async with factory() as db:
            db.add(
                NotificationPreference(
                    user_id=user_id,
                    tenant_id=tenant.id,
                    channel="telegram",
                    channel_config='{"chat_id":"should-not-send"}',
                    enabled=True,
                )
            )
            await db.commit()

        sent = await send_notification(
            tenant_id=tenant.id,
            event_type="new_rfq",
            message="This must remain inside the retirement gate.",
        )
        assert sent == 0

        async with factory() as db:
            event = (
                await db.exec(
                    select(RetirementUsageEvent)
                    .where(RetirementUsageEvent.tenant_id == tenant.id)
                    .where(RetirementUsageEvent.candidate_key == "notification_telegram")
                    .where(RetirementUsageEvent.event_name == "enabled_preference_dispatch_blocked")
                )
            ).first()
            assert event is not None
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_removed_scoring_endpoint_and_remaining_retirement_report(
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

        removed_ml = await http_client.get(
            "/api/v1/tracking/ml/status", headers=tenant_headers
        )
        assert removed_ml.status_code == 404

        report = await http_client.get(
            "/api/v1/admin/retirement-audit", headers=platform_headers
        )
        assert report.status_code == 200, report.text
        candidates = {
            item["candidate_key"]: item for item in report.json()["candidates"]
        }
        assert {
            "notification_telegram",
            "notification_line",
            "relation_recommender",
            "legacy_ip_resolver",
        } <= set(candidates)
        assert "ml_scoring_runtime" not in candidates
        assert "copilot_floating_widget" not in candidates
        assert candidates["legacy_ip_resolver"]["status"] == "removed"
        for channel_candidate in ("notification_telegram", "notification_line"):
            assert candidates[channel_candidate]["code_state"] == "disabled"
            assert candidates[channel_candidate]["status"] == "observing"
            assert candidates[channel_candidate]["evidence"]["enabled_preferences"] == 0
            assert "observation_window_incomplete" in candidates[channel_candidate]["blockers"]
        removed_candidate = await http_client.put(
            "/api/v1/admin/retirement-audit/ml_scoring_runtime/decision",
            headers=platform_headers,
            json={
                "status": "approved_removal",
                "reason": "Attempted before the mandatory evidence window was complete.",
            },
        )
        assert removed_candidate.status_code == 404

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


@requires_db
@pytest.mark.asyncio
async def test_removal_approval_requires_governance_evidence(http_client) -> None:
    engine, factory = _make_engine()
    platform_id, platform_token = await _create_superuser(factory)
    candidate_key = f"governance_test_{uuid.uuid4().hex[:12]}"
    headers = _auth(platform_token)
    try:
        async with factory() as db:
            db.add(
                RetirementCandidateObservation(
                    candidate_key=candidate_key,
                    display_name="Governance gate test candidate",
                    required_observation_days=30,
                    code_state="disabled",
                    status="observing",
                    started_at=utcnow_naive() - timedelta(days=31),
                )
            )
            await db.commit()

        report = await http_client.get(
            "/api/v1/admin/retirement-audit", headers=headers
        )
        assert report.status_code == 200, report.text
        assert len(report.json()["report_sha256"]) == 64
        candidate = next(
            item
            for item in report.json()["candidates"]
            if item["candidate_key"] == candidate_key
        )
        assert candidate["technical_removal_ready"] is True
        assert candidate["removal_ready"] is False
        assert "telemetry_continuity_unverified" in candidate["blockers"]

        missing = await http_client.put(
            f"/api/v1/admin/retirement-audit/{candidate_key}/decision",
            headers=headers,
            json={
                "status": "approved_removal",
                "reason": "The technical window passed but governance evidence is intentionally absent.",
            },
        )
        assert missing.status_code == 409
        assert "telemetry_evidence_ref" in missing.text

        approved = await http_client.put(
            f"/api/v1/admin/retirement-audit/{candidate_key}/decision",
            headers=headers,
            json={
                "status": "approved_removal",
                "reason": "All technical and governance evidence has been independently recorded.",
                "telemetry_evidence_ref": "evidence://retirement/continuous-31-days",
                "data_disposition": "not_applicable",
                "rollback_revision": "a" * 40,
                "removal_plan_ref": "change://retirement/isolated-removal-plan",
            },
        )
        assert approved.status_code == 200, approved.text
        payload = approved.json()
        assert payload["status"] == "approved_removal"
        assert payload["removal_ready"] is True
        assert payload["decision"]["telemetry_verified_by"] == str(platform_id)
        assert payload["decision"]["data_disposition"] == "not_applicable"

        async with factory() as db:
            stored = await db.get(RetirementCandidateObservation, candidate_key)
            assert stored
            stored.telemetry_verified_by = None
            db.add(stored)
            await db.commit()
        no_actor_report = await http_client.get(
            "/api/v1/admin/retirement-audit", headers=headers
        )
        no_actor = next(
            item
            for item in no_actor_report.json()["candidates"]
            if item["candidate_key"] == candidate_key
        )
        assert no_actor["removal_ready"] is False
        assert "telemetry_continuity_unverified" in no_actor["blockers"]
    finally:
        async with factory() as db:
            await db.exec(
                text(
                    "DELETE FROM platform_audit_logs "
                    "WHERE actor_user_id = :id OR target_id = :candidate"
                ),
                params={"id": str(platform_id), "candidate": candidate_key},
            )
            await db.exec(
                text(
                    "DELETE FROM retirement_candidate_observations "
                    "WHERE candidate_key = :candidate"
                ),
                params={"candidate": candidate_key},
            )
            await db.exec(
                text("DELETE FROM users WHERE id = :id"),
                params={"id": str(platform_id)},
            )
            await db.commit()
        await engine.dispose()
