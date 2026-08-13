import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_check_reports_dependencies():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")

    # DB-backed checks may be unavailable in unit-only environments, but the
    # endpoint must expose the full readiness contract instead of a fixed ok.
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["status"] in ("ready", "degraded")
    assert set(body["checks"]) == {"database", "migration", "storage", "scheduler"}
