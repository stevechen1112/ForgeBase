"""Deterministic internal capacity baseline; not a production load claim."""

from __future__ import annotations

import asyncio
import gc
import json
import os
import time
import tracemalloc
import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import delete, text
from sqlmodel import select

from app.models.operational_job import OperationalJob
from app.models.product import Product
from app.models.product_category import ProductCategory
from app.services import operational_outbox
from tests.conftest import _make_engine, requires_db


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * percentile) - 1))
    return ordered[index]


def _write_report(payload: dict[str, Any]) -> None:
    target = os.getenv("FORGEBASE_PERFORMANCE_REPORT")
    if not target:
        return
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@pytest.mark.asyncio
@pytest.mark.performance
@requires_db
async def test_api_capacity_queue_throughput_and_short_soak(
    http_client, two_tenants, monkeypatch
):
    tenant, _other_tenant = two_tenants
    engine, factory = _make_engine()
    product_count = 800
    request_count = 180
    concurrency = 18
    queue_count = 300

    category = ProductCategory(
        tenant_id=tenant.id,
        category_name="Capacity fixtures",
        slug=f"capacity-{uuid.uuid4().hex[:8]}",
        status="published",
        locale="en",
    )
    async with factory() as db:
        db.add(category)
        await db.flush()
        db.add_all(
            [
                Product(
                    tenant_id=tenant.id,
                    category_id=category.id,
                    product_name=f"Capacity Product {index:04d}",
                    slug=f"capacity-product-{index:04d}-{category.id.hex[:6]}",
                    model_number=f"CAP-{category.id.hex[:6]}-{index:04d}",
                    short_description="Deterministic capacity fixture",
                    status="published",
                    locale="en",
                    display_priority=index % 10,
                )
                for index in range(product_count)
            ]
        )
        await db.commit()
        await db.exec(text("ANALYZE products"))
        await db.commit()

    headers = {"X-Tenant-ID": str(tenant.id)}
    path = "/api/v1/content/products?page_size=100&status=published&locale=en"
    for _ in range(5):
        warm = await http_client.get(path, headers=headers)
        assert warm.status_code == 200

    semaphore = asyncio.Semaphore(concurrency)

    async def timed_get() -> tuple[int, float]:
        async with semaphore:
            started = time.perf_counter()
            response = await http_client.get(path, headers=headers)
            return response.status_code, (time.perf_counter() - started) * 1000

    started = time.perf_counter()
    results = await asyncio.gather(*(timed_get() for _ in range(request_count)))
    elapsed = time.perf_counter() - started
    tracemalloc.start()
    gc.collect()
    before_memory, _ = tracemalloc.get_traced_memory()
    soak_results = []
    for _wave in range(4):
        soak_results.extend(await asyncio.gather(*(timed_get() for _ in range(10))))
    gc.collect()
    after_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    statuses = Counter(status for status, _latency in results)
    latencies = [latency for _status, latency in results]
    api_p50 = _percentile(latencies, 0.50)
    api_p95 = _percentile(latencies, 0.95)
    requests_per_second = request_count / elapsed
    retained_memory_mb = max(0, after_memory - before_memory) / (1024 * 1024)
    peak_memory_mb = peak_memory / (1024 * 1024)

    assert statuses == {200: request_count}
    assert all(status == 200 for status, _latency in soak_results)
    assert api_p95 < 1_000
    assert requests_per_second >= 10
    assert retained_memory_mb < 32

    @asynccontextmanager
    async def session_context():
        async with factory() as session:
            yield session

    monkeypatch.setattr(operational_outbox, "get_session_ctx", session_context)

    from app.services.inbound_reply import runtime as inbound_runtime

    async def noop(_db):
        return 0

    monkeypatch.setattr(inbound_runtime, "redact_expired_inbound_content", noop)
    monkeypatch.setattr(inbound_runtime, "mark_breached_handoff_slas", noop)

    effects: Counter[str] = Counter()

    async def execute(job: OperationalJob) -> None:
        effects[job.idempotency_key] += 1

    monkeypatch.setattr(operational_outbox, "_execute", execute)
    job_ids: list[uuid.UUID] = []
    async with factory() as db:
        for index in range(queue_count):
            job = OperationalJob(
                tenant_id=tenant.id,
                job_type="capacity_lab",
                payload_json="{}",
                idempotency_key=f"capacity:{category.id}:{index}",
            )
            job_ids.append(job.id)
            db.add(job)
        await db.commit()

    queue_started = time.perf_counter()
    queue_stats: list[dict[str, int]] = []
    for _wave in range(4):
        queue_stats.extend(
            await asyncio.gather(
                *(
                    operational_outbox.process_operational_jobs(
                        limit=75, job_types={"capacity_lab"}
                    )
                    for _ in range(4)
                )
            )
        )
        async with factory() as db:
            remaining = list(
                (
                    await db.exec(
                        select(OperationalJob.id).where(
                            OperationalJob.id.in_(job_ids),
                            OperationalJob.status != "completed",
                        )
                    )
                ).all()
            )
        if not remaining:
            break
    queue_elapsed = time.perf_counter() - queue_started
    queue_per_second = queue_count / queue_elapsed
    async with factory() as db:
        completed = list(
            (
                await db.exec(
                    select(OperationalJob).where(OperationalJob.id.in_(job_ids))
                )
            ).all()
        )
        await db.exec(text("SET LOCAL enable_seqscan = off"))
        plan = (
            await db.exec(
                text(
                    """
                    EXPLAIN (FORMAT TEXT)
                    SELECT id FROM products
                    WHERE tenant_id = :tenant_id
                      AND locale = 'en'
                      AND status = 'published'
                    ORDER BY display_priority DESC, product_name
                    LIMIT 100
                    """
                ),
                params={"tenant_id": tenant.id},
            )
        ).all()

    assert len(completed) == queue_count
    assert all(job.status == "completed" for job in completed)
    assert len(effects) == queue_count
    assert set(effects.values()) == {1}
    assert sum(item["completed"] for item in queue_stats) == queue_count
    assert queue_per_second >= 40
    plan_text = "\n".join(str(row[0]) for row in plan)
    assert "ix_products_public_listing" in plan_text

    _write_report(
        {
            "schema_version": 1,
            "lab": "performance-capacity-soak",
            "status": "passed",
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "dataset": {"products": product_count, "queue_jobs": queue_count},
            "api": {
                "requests": request_count,
                "short_soak_requests": len(soak_results),
                "concurrency": concurrency,
                "failures": request_count - statuses[200],
                "p50_ms": round(api_p50, 2),
                "p95_ms": round(api_p95, 2),
                "requests_per_second": round(requests_per_second, 2),
                "retained_memory_mb": round(retained_memory_mb, 2),
                "peak_traced_memory_mb": round(peak_memory_mb, 2),
            },
            "queue": {
                "jobs": queue_count,
                "workers": 4,
                "failures": sum(item["failed"] for item in queue_stats),
                "jobs_per_second": round(queue_per_second, 2),
                "duplicate_effects": sum(
                    max(0, count - 1) for count in effects.values()
                ),
            },
            "thresholds": {
                "api_p95_ms_lt": 1_000,
                "api_requests_per_second_gte": 10,
                "retained_memory_mb_lt": 32,
                "queue_jobs_per_second_gte": 40,
            },
            "external_network_calls": 0,
            "public_listing_index_used": True,
        }
    )

    async with factory() as db:
        await db.exec(delete(OperationalJob).where(OperationalJob.id.in_(job_ids)))
        await db.commit()
    await engine.dispose()
