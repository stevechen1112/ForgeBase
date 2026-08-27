"""Durable SLO sampling and operator-visible incident lifecycle acceptance."""

import json
import uuid
from datetime import timedelta

import pytest
from app.core.datetime import utcnow_naive
from app.models.observability import (
    OperationalIncident,
    OperationalIncidentEvent,
    ServiceLevelSnapshot,
)
from app.models.operational_job import OperationalJob
from sqlalchemy import delete
from sqlmodel import select

from tests.conftest import _make_engine, requires_db
from tests.test_platform_tenant_operations import (
    _auth,
    _create_platform_superuser,
    _delete_platform_superuser,
)


@requires_db
@pytest.mark.asyncio
async def test_slo_sampling_and_incident_lifecycle_are_durable(
    http_client,
    two_tenants,
) -> None:
    tenant, _ = two_tenants
    operator_id, token = await _create_platform_superuser()
    engine, factory = _make_engine()
    failed_id = uuid.uuid4()
    stale_id = uuid.uuid4()
    now = utcnow_naive()
    try:
        async with factory() as session:
            await session.exec(delete(OperationalIncidentEvent))
            await session.exec(delete(OperationalIncident))
            await session.exec(delete(ServiceLevelSnapshot))
            for index in range(20):
                session.add(
                    OperationalJob(
                        id=failed_id if index == 0 else uuid.uuid4(),
                        tenant_id=tenant.id,
                        job_type="acceptance_probe",
                        payload_json=json.dumps({"sequence": index}),
                        status="failed" if index == 0 else "completed",
                        last_error="injected terminal failure" if index == 0 else None,
                        idempotency_key=f"slo-{uuid.uuid4()}",
                        completed_at=None if index == 0 else now,
                        updated_at=now,
                    )
                )
            session.add(
                OperationalJob(
                    id=stale_id,
                    tenant_id=tenant.id,
                    job_type="acceptance_stale_probe",
                    payload_json="{}",
                    status="processing",
                    locked_at=now - timedelta(hours=2),
                    idempotency_key=f"slo-stale-{uuid.uuid4()}",
                    updated_at=now,
                )
            )
            await session.commit()

        sampled = await http_client.post(
            "/api/v1/admin/operations/slo/sample", headers=_auth(token)
        )
        assert sampled.status_code == 200, sampled.text
        assert sampled.json()["status"] == "breached"
        assert "failed_operational_jobs" in sampled.json()["breached"]

        listed = await http_client.get(
            "/api/v1/admin/operations/incidents", headers=_auth(token)
        )
        assert listed.status_code == 200, listed.text
        active = {
            item["incident_key"]: item
            for item in listed.json()["items"]
            if item["status"] != "resolved"
        }
        assert {"failed-operational-jobs", "stale-queue-claims"} <= set(active)
        failure = active["failed-operational-jobs"]
        assert [event["action"] for event in failure["events"]] == ["opened"]

        acknowledged = await http_client.post(
            f"/api/v1/admin/operations/incidents/{failure['id']}/actions",
            json={"action": "acknowledge", "note": "已確認測試注入失敗，正在處理"},
            headers=_auth(token),
        )
        assert acknowledged.status_code == 200, acknowledged.text
        assert acknowledged.json()["status"] == "acknowledged"
        duplicate_ack = await http_client.post(
            f"/api/v1/admin/operations/incidents/{failure['id']}/actions",
            json={"action": "acknowledge", "note": "重複確認不應新增稽核狀態事件"},
            headers=_auth(token),
        )
        assert duplicate_ack.status_code == 409

        resampled = await http_client.post(
            "/api/v1/admin/operations/slo/sample", headers=_auth(token)
        )
        assert resampled.status_code == 200
        listed_again = await http_client.get(
            "/api/v1/admin/operations/incidents", headers=_auth(token)
        )
        repeated = next(
            item
            for item in listed_again.json()["items"]
            if item["incident_key"] == "failed-operational-jobs"
        )
        assert repeated["id"] == failure["id"]
        assert repeated["occurrence_count"] == 2
        assert [event["action"] for event in repeated["events"]].count("opened") == 1

        resolved_while_active = await http_client.post(
            f"/api/v1/admin/operations/incidents/{failure['id']}/actions",
            json={"action": "resolve", "note": "先標記已完成人工處置，交由監控複核"},
            headers=_auth(token),
        )
        assert resolved_while_active.status_code == 200
        reopened_sample = await http_client.post(
            "/api/v1/admin/operations/slo/sample", headers=_auth(token)
        )
        assert reopened_sample.status_code == 200
        reopened_list = await http_client.get(
            "/api/v1/admin/operations/incidents", headers=_auth(token)
        )
        reopened = next(
            item
            for item in reopened_list.json()["items"]
            if item["incident_key"] == "failed-operational-jobs"
        )
        assert reopened["status"] == "open"
        assert reopened["acknowledged_at"] is None
        assert "reopened" in [event["action"] for event in reopened["events"]]

        async with factory() as session:
            failed = await session.get(OperationalJob, failed_id)
            stale = await session.get(OperationalJob, stale_id)
            assert failed and stale
            failed.status = "completed"
            failed.last_error = None
            failed.completed_at = now
            failed.updated_at = now
            stale.status = "completed"
            stale.locked_at = None
            stale.completed_at = now
            stale.updated_at = now
            session.add(failed)
            session.add(stale)
            await session.commit()

        recovered = await http_client.post(
            "/api/v1/admin/operations/slo/sample", headers=_auth(token)
        )
        assert recovered.status_code == 200
        final_list = await http_client.get(
            "/api/v1/admin/operations/incidents", headers=_auth(token)
        )
        assert all(item["status"] == "resolved" for item in final_list.json()["items"])

        levels = await http_client.get(
            "/api/v1/admin/operations/slo?history_limit=10", headers=_auth(token)
        )
        assert levels.status_code == 200
        assert len(levels.json()["history"]) == 4
        assert levels.json()["external_uptime_claimed"] is False

        async with factory() as session:
            event_actions = (
                await session.exec(
                    select(OperationalIncidentEvent.action).where(
                        OperationalIncidentEvent.incident_id == uuid.UUID(failure["id"])
                    )
                )
            ).all()
            assert "acknowledged" in event_actions
            assert "resolved" in event_actions
    finally:
        async with factory() as session:
            await session.exec(delete(OperationalIncidentEvent))
            await session.exec(delete(OperationalIncident))
            await session.exec(delete(ServiceLevelSnapshot))
            await session.commit()
        await engine.dispose()
        await _delete_platform_superuser(operator_id)
