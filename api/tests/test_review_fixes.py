"""Cross-cutting regression tests retained after RFQ scope realignment."""

import asyncio
import uuid

from app.main import app
from tests.conftest import requires_db


def test_retired_crm_and_unverifiable_handoff_routes_are_not_registered():
    """Retired features must be absent from the runtime API, not merely hidden in UI."""
    paths = set(app.openapi()["paths"])
    retired_paths = {
        "/api/v1/tracking/outcomes",
        "/api/v1/tracking/funnel",
        "/api/v1/tracking/analytics/funnel",
        "/api/v1/tracking/rfqs/{rfq_id}/follow-up",
        "/api/v1/tracking/sales-handoffs/{handoff_id}/start",
        "/api/v1/tracking/sales-handoffs/{handoff_id}/contacted",
    }
    assert paths.isdisjoint(retired_paths)


@requires_db
async def test_idempotency_concurrent_same_key_returns_same_page(http_client, two_tenants, admin_token_for_tenant):
    tenant, _ = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    key = f"cf-concurrent-{uuid.uuid4()}"
    slug = f"idem-par-{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}
    payload = {"page_type": "blog_post", "slug": slug, "title": "Concurrent", "body": "<p>x</p>", "locale": "en", "status": "draft"}
    first, second = await asyncio.gather(
        http_client.post("/api/v1/content/pages", json=payload, headers=headers),
        http_client.post("/api/v1/content/pages", json=payload, headers=headers),
    )
    assert first.status_code in (200, 201) and second.status_code in (200, 201)
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


@requires_db
async def test_has_rfq_uses_rfq_requests_not_tracking_event(http_client, two_tenants, admin_token_for_tenant):
    tenant, _ = two_tenants
    visitor_id, session_id = uuid.uuid4(), uuid.uuid4()
    public = {"X-Tenant-ID": str(tenant.id)}
    await http_client.post("/api/v1/tracking/events", headers=public, json={"event_name": "certification_view", "visitor_id": str(visitor_id), "session_id": str(session_id), "page_url": "https://example.test/cert", "analytics_consent": True})
    response = await http_client.post("/api/v1/forms/rfq", headers=public, json={"full_name": "Buyer", "email": f"noevt-{uuid.uuid4().hex[:8]}@acme.com", "company_name": "Acme", "country": "DE", "consent": True, "product_ids": [], "visitor_id": str(visitor_id), "message": "Please review the attached requirements."})
    assert response.status_code == 201
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant.id)}"}
    with_rfq = await http_client.get("/api/v1/tracking/visitors?has_rfq=true", headers=auth)
    without_rfq = await http_client.get("/api/v1/tracking/visitors?has_rfq=false", headers=auth)
    assert str(visitor_id) in [row["visitor_id"] for row in with_rfq.json()]
    assert str(visitor_id) not in [row["visitor_id"] for row in without_rfq.json()]


@requires_db
async def test_task_queue_draft_link_points_to_pages(http_client, two_tenants, admin_token_for_tenant):
    tenant, _ = two_tenants
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant.id)}"}
    data = (await http_client.get("/api/v1/ops/task-queue", headers=auth)).json()
    draft = next(item for item in data["tasks"] if item["type"] == "content_pending_approval")
    assert draft["link"] == "/dashboard/pages"


@requires_db
async def test_task_queue_includes_draft_products(http_client, two_tenants, admin_token_for_tenant):
    tenant, _ = two_tenants
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant.id)}"}
    before = (await http_client.get("/api/v1/ops/task-queue", headers=auth)).json()
    before_drafts = next(item for item in before["tasks"] if item["type"] == "content_pending_approval")

    category = await http_client.post(
        "/api/v1/content/categories",
        headers=auth,
        json={
            "category_name": "Queue category",
            "slug": f"queue-category-{uuid.uuid4().hex[:8]}",
            "locale": "en",
            "status": "published",
        },
    )
    assert category.status_code == 201, category.text
    product = await http_client.post(
        "/api/v1/content/products",
        headers=auth,
        json={
            "product_name": "Queue draft product",
            "slug": f"queue-product-{uuid.uuid4().hex[:8]}",
            "model_number": f"QUEUE-{uuid.uuid4().hex[:8]}",
            "short_description": "A draft product for the operational queue.",
            "category_id": category.json()["data"]["id"],
            "locale": "en",
            "status": "draft",
        },
    )
    assert product.status_code == 201, product.text

    after = (await http_client.get("/api/v1/ops/task-queue", headers=auth)).json()
    after_drafts = next(item for item in after["tasks"] if item["type"] == "content_pending_approval")
    assert after_drafts["count"] == before_drafts["count"] + 1
    assert any(
        item["id"] == product.json()["data"]["id"] and item["content_type"] == "products"
        for item in after_drafts["items"]
    )
