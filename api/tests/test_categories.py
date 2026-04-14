"""Tests for /api/v1/content/categories endpoints."""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport

from app.main import app
from tests.conftest import requires_db


# ── auth guard tests (no DB needed) ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_category_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/content/categories",
            json={
                "category_name": "Fasteners",
                "slug": "fasteners",
                "locale": "en",
                "status": "draft",
            },
        )
        # No auth header → HTTPBearer raises 403
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_delete_category_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(f"/api/v1/content/categories/{uuid.uuid4()}")
        assert resp.status_code in (401, 403)


# ── DB integration tests (skipped locally when no DB) ────────────────────────
@requires_db
@pytest.mark.asyncio
async def test_list_categories_empty(http_client):
    resp = await http_client.get("/api/v1/content/categories")
    assert resp.status_code == 200
    assert "data" in resp.json()


@requires_db
@pytest.mark.asyncio
async def test_get_nonexistent_category_returns_404(http_client):
    resp = await http_client.get(f"/api/v1/content/categories/{uuid.uuid4()}")
    assert resp.status_code == 404

