"""Concurrent fault-injection and endurance proof for durable internal queues."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, func, text, update
from sqlmodel import select

from app.core.datetime import utcnow_naive
from app.models.knowledge import KnowledgeSyncJob
from app.models.operational_job import OperationalJob
from app.models.tenant import Tenant
from app.services import knowledge_sync, operational_outbox
from app.services.company_identification.providers.base import (
    CompanyProviderPermanentError,
)
from app.services.rfq_auto_reply import AutoReplyDeferred
from tests.conftest import _make_engine, requires_db


class InjectedTransientError(RuntimeError):
    retry_after_seconds = 1


def _write_report(payload: dict[str, Any]) -> None:
    target = os.getenv("FORGEBASE_FAULT_REPORT")
    if not target:
        return
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@pytest.mark.asyncio
@requires_db
async def test_concurrent_fault_injection_and_queue_endurance(monkeypatch):
    engine, factory = _make_engine()

    @asynccontextmanager
    async def session_context():
        async with factory() as session:
            yield session

    monkeypatch.setattr(operational_outbox, "get_session_ctx", session_context)
    monkeypatch.setattr(knowledge_sync, "get_session_ctx", session_context)

    from app.services.inbound_reply import runtime as inbound_runtime

    maintenance_calls = 0

    async def fail_retention(_db):
        nonlocal maintenance_calls
        maintenance_calls += 1
        if maintenance_calls == 1:
            await _db.exec(text("SELECT 1 / 0"))
        return 0

    async def healthy_sla_scan(_db):
        return 0

    monkeypatch.setattr(
        inbound_runtime, "redact_expired_inbound_content", fail_retention
    )
    monkeypatch.setattr(inbound_runtime, "mark_breached_handoff_slas", healthy_sla_scan)

    tag = uuid.uuid4().hex[:10]
    tenant = Tenant(name=f"Fault Lab {tag}", slug=f"fault-lab-{tag}")
    operational_calls: dict[str, int] = defaultdict(int)
    operational_effects: dict[str, int] = defaultdict(int)
    knowledge_calls: dict[uuid.UUID, int] = defaultdict(int)
    knowledge_effects: dict[uuid.UUID, int] = defaultdict(int)
    operational_ids: list[uuid.UUID] = []
    knowledge_ids: list[uuid.UUID] = []
    bulk_operational = 160
    bulk_knowledge = 120

    try:
        async with factory() as db:
            db.add(tenant)
            await db.commit()
            await db.refresh(tenant)

            for index in range(bulk_operational):
                mode = "transient" if index % 10 == 0 else "ok"
                job = OperationalJob(
                    tenant_id=tenant.id,
                    job_type="fault_lab",
                    payload_json=json.dumps({"mode": mode}),
                    idempotency_key=f"fault:{tag}:operational:{index}",
                )
                operational_ids.append(job.id)
                db.add(job)

            special_operational = (
                OperationalJob(
                    tenant_id=tenant.id,
                    job_type="fault_lab",
                    payload_json=json.dumps({"mode": "permanent"}),
                    idempotency_key=f"fault:{tag}:operational:permanent",
                ),
                OperationalJob(
                    tenant_id=tenant.id,
                    job_type="fault_lab",
                    payload_json=json.dumps({"mode": "exhaust"}),
                    max_attempts=2,
                    idempotency_key=f"fault:{tag}:operational:exhaust",
                ),
                OperationalJob(
                    tenant_id=tenant.id,
                    job_type="fault_lab",
                    payload_json=json.dumps({"mode": "deferred"}),
                    idempotency_key=f"fault:{tag}:operational:deferred",
                ),
                OperationalJob(
                    tenant_id=tenant.id,
                    job_type="fault_lab",
                    payload_json=json.dumps({"mode": "stale"}),
                    status="processing",
                    attempts=1,
                    locked_at=utcnow_naive() - timedelta(minutes=11),
                    idempotency_key=f"fault:{tag}:operational:stale",
                ),
            )
            for job in special_operational:
                operational_ids.append(job.id)
                db.add(job)

            transient_knowledge_ids: set[uuid.UUID] = set()
            rollback_source_id: uuid.UUID | None = None
            for index in range(bulk_knowledge):
                source_id = uuid.uuid4()
                if index % 10 == 0:
                    transient_knowledge_ids.add(source_id)
                    if rollback_source_id is None:
                        rollback_source_id = source_id
                job = KnowledgeSyncJob(
                    tenant_id=tenant.id,
                    source_type="product",
                    source_id=source_id,
                    dedupe_key=f"fault:{tag}:knowledge:{index}",
                )
                knowledge_ids.append(job.id)
                db.add(job)

            exhausted_source_id = uuid.uuid4()
            stale_source_id = uuid.uuid4()
            special_knowledge = (
                KnowledgeSyncJob(
                    tenant_id=tenant.id,
                    source_type="product",
                    source_id=exhausted_source_id,
                    max_attempts=2,
                    dedupe_key=f"fault:{tag}:knowledge:exhaust",
                ),
                KnowledgeSyncJob(
                    tenant_id=tenant.id,
                    source_type="product",
                    source_id=stale_source_id,
                    status="running",
                    attempts=1,
                    locked_at=utcnow_naive() - timedelta(minutes=11),
                    dedupe_key=f"fault:{tag}:knowledge:stale",
                ),
            )
            for job in special_knowledge:
                knowledge_ids.append(job.id)
                db.add(job)
            await db.commit()

        async def execute_operational(job: OperationalJob) -> None:
            key = job.idempotency_key
            operational_calls[key] += 1
            mode = json.loads(job.payload_json)["mode"]
            if mode == "permanent":
                raise CompanyProviderPermanentError("injected permanent rejection")
            if mode == "exhaust":
                raise InjectedTransientError("injected persistent outage")
            if mode == "deferred" and operational_calls[key] == 1:
                raise AutoReplyDeferred(1)
            if mode == "transient" and operational_calls[key] == 1:
                raise InjectedTransientError("injected provider timeout")
            operational_effects[key] += 1

        async def compile_knowledge(
            _db, *, tenant_id, source_type, source_id
        ) -> None:
            assert tenant_id == tenant.id
            assert source_type == "product"
            knowledge_calls[source_id] += 1
            if source_id == exhausted_source_id:
                raise InjectedTransientError("injected extractor outage")
            if source_id == rollback_source_id and knowledge_calls[source_id] == 1:
                await _db.exec(text("SELECT 1 / 0"))
            if (
                source_id in transient_knowledge_ids
                and knowledge_calls[source_id] == 1
            ):
                raise InjectedTransientError("injected transient extractor timeout")
            knowledge_effects[source_id] += 1

        backfill_calls = 0

        async def fail_backfill(_db):
            nonlocal backfill_calls
            backfill_calls += 1
            if backfill_calls == 1:
                raise RuntimeError("injected backfill outage")
            return {"tenants": 0}

        monkeypatch.setattr(operational_outbox, "_execute", execute_operational)
        monkeypatch.setattr(knowledge_sync, "compile_source", compile_knowledge)
        monkeypatch.setattr(knowledge_sync, "backfill_missing_knowledge", fail_backfill)

        operational_stats: list[dict[str, int]] = []
        knowledge_stats: list[dict[str, int]] = []
        for _wave in range(8):
            op_wave, knowledge_wave = await asyncio.gather(
                asyncio.gather(
                    *(operational_outbox.process_operational_jobs(limit=45) for _ in range(4))
                ),
                asyncio.gather(
                    *(knowledge_sync.process_knowledge_sync_jobs(limit=35) for _ in range(4))
                ),
            )
            operational_stats.extend(op_wave)
            knowledge_stats.extend(knowledge_wave)
            async with factory() as db:
                await db.exec(
                    update(OperationalJob)
                    .where(
                        OperationalJob.id.in_(operational_ids),
                        OperationalJob.status == "retry",
                    )
                    .values(available_at=datetime(2000, 1, 1))
                )
                await db.exec(
                    update(KnowledgeSyncJob)
                    .where(
                        KnowledgeSyncJob.id.in_(knowledge_ids),
                        KnowledgeSyncJob.status == "queued",
                    )
                    .values(available_at=datetime(2000, 1, 1))
                )
                active_operational = int(
                    (
                        await db.exec(
                            select(func.count(OperationalJob.id)).where(
                                OperationalJob.id.in_(operational_ids),
                                OperationalJob.status.in_(
                                    ["pending", "retry", "processing"]
                                ),
                            )
                        )
                    ).one()
                    or 0
                )
                active_knowledge = int(
                    (
                        await db.exec(
                            select(func.count(KnowledgeSyncJob.id)).where(
                                KnowledgeSyncJob.id.in_(knowledge_ids),
                                KnowledgeSyncJob.status.in_(["queued", "running"]),
                            )
                        )
                    ).one()
                    or 0
                )
                await db.commit()
            if not active_operational and not active_knowledge:
                break

        async with factory() as db:
            operational_rows = list(
                (
                    await db.exec(
                        select(OperationalJob).where(
                            OperationalJob.id.in_(operational_ids)
                        )
                    )
                ).all()
            )
            knowledge_rows = list(
                (
                    await db.exec(
                        select(KnowledgeSyncJob).where(
                            KnowledgeSyncJob.id.in_(knowledge_ids)
                        )
                    )
                ).all()
            )

        operational_by_mode = {
            json.loads(row.payload_json)["mode"]: row
            for row in operational_rows
            if json.loads(row.payload_json)["mode"] != "ok"
            and json.loads(row.payload_json)["mode"] != "transient"
        }
        assert len(operational_rows) == bulk_operational + 4
        assert sum(row.status == "completed" for row in operational_rows) == (
            bulk_operational + 2
        )
        assert operational_by_mode["permanent"].status == "failed"
        assert operational_by_mode["permanent"].attempts == 1
        assert operational_by_mode["exhaust"].status == "failed"
        assert operational_by_mode["exhaust"].attempts == 2
        assert operational_by_mode["deferred"].status == "completed"
        assert operational_by_mode["deferred"].attempts == 1
        assert operational_by_mode["stale"].status == "completed"
        assert operational_by_mode["stale"].attempts == 2
        assert all(row.locked_at is None for row in operational_rows)
        assert all(row.attempts <= row.max_attempts for row in operational_rows)

        knowledge_by_source = {row.source_id: row for row in knowledge_rows}
        assert len(knowledge_rows) == bulk_knowledge + 2
        assert sum(row.status == "succeeded" for row in knowledge_rows) == (
            bulk_knowledge + 1
        )
        assert knowledge_by_source[exhausted_source_id].status == "failed"
        assert knowledge_by_source[exhausted_source_id].attempts == 2
        assert knowledge_by_source[stale_source_id].status == "succeeded"
        assert knowledge_by_source[stale_source_id].attempts == 2
        assert all(row.locked_at is None for row in knowledge_rows)
        assert all(row.attempts <= row.max_attempts for row in knowledge_rows)

        normal_operational_calls = [
            count
            for key, count in operational_calls.items()
            if key.startswith(f"fault:{tag}:operational:")
            and not key.endswith(("exhaust", "deferred"))
        ]
        assert max(normal_operational_calls) <= 2
        assert max(
            count
            for source_id, count in knowledge_calls.items()
            if source_id != exhausted_source_id
        ) <= 2
        assert len(operational_effects) == bulk_operational + 2
        assert set(operational_effects.values()) == {1}
        assert len(knowledge_effects) == bulk_knowledge + 1
        assert set(knowledge_effects.values()) == {1}
        assert maintenance_calls > 0
        assert backfill_calls > 0

        duplicate_terminal_effects = sum(
            max(0, count - 1) for count in operational_effects.values()
        ) + sum(max(0, count - 1) for count in knowledge_effects.values())

        _write_report(
            {
                "schema_version": 1,
                "lab": "fault-injection-endurance",
                "status": "passed",
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "workers_per_queue": 4,
                "operational_jobs": len(operational_rows),
                "knowledge_jobs": len(knowledge_rows),
                "operational_terminal": len(operational_rows),
                "knowledge_terminal": len(knowledge_rows),
                "maintenance_failures_injected": 1,
                "backfill_failures_injected": 1,
                "operational_retries": sum(
                    item["retried"] for item in operational_stats
                ),
                "knowledge_retries": sum(item["retried"] for item in knowledge_stats),
                "external_network_calls": 0,
                "duplicate_terminal_effects": duplicate_terminal_effects,
            }
        )
    finally:
        async with factory() as db:
            await db.exec(
                delete(OperationalJob).where(OperationalJob.tenant_id == tenant.id)
            )
            await db.exec(
                delete(KnowledgeSyncJob).where(KnowledgeSyncJob.tenant_id == tenant.id)
            )
            await db.exec(delete(Tenant).where(Tenant.id == tenant.id))
            await db.commit()
        await engine.dispose()
