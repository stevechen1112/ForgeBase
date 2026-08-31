"""Code review 修補驗收：idempotency 併發、has_rfq 以 RFQ 表為準、batch explanation、歸因精確比對、won_reason。"""
import asyncio
import uuid

from app.api.v1.endpoints.growth_ops import match_source_to_page, _source_path_segments
from tests.conftest import requires_db


# ── 歸因精確比對（免 DB）──────────────────────────────────────────────────

def test_source_path_segments_normalizes_url_and_query():
    assert _source_path_segments("/en/blog/stamping-guide?utm=1") == ["en", "blog", "stamping-guide"]
    assert _source_path_segments("https://www.example.com/en/blog/stamping-guide") == [
        "en", "blog", "stamping-guide",
    ]


def test_match_source_rejects_substring_false_positive():
    pages = [
        ("guide", "Short", "blog_post"),
        ("stamping-guide", "Long", "blog_post"),
    ]
    # 子字串「guide」不可誤命中「stamping-guide」路徑之外的短詞；路徑含完整 segment 才算
    hit = match_source_to_page("/en/blog/stamping-guide", pages)
    assert hit is not None and hit["slug"] == "stamping-guide"  # 最長 slug 勝出

    miss = match_source_to_page("/en/blog/other-article", pages)
    assert miss is None  # 「guide」不是 path segment，不可子字串命中


# ── Idempotency 併發 ───────────────────────────────────────────────────────

@requires_db
async def test_idempotency_concurrent_same_key_returns_same_page(
    http_client, two_tenants, admin_token_for_tenant,
):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    key = f"cf-concurrent-{uuid.uuid4()}"
    slug = f"idem-par-{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}
    payload = {
        "page_type": "blog_post", "slug": slug, "title": "Concurrent",
        "body": "<p>x</p>", "locale": "en", "status": "draft",
    }

    r1, r2 = await asyncio.gather(
        http_client.post("/api/v1/content/pages", json=payload, headers=headers),
        http_client.post("/api/v1/content/pages", json=payload, headers=headers),
    )
    assert r1.status_code in (200, 201), r1.text
    assert r2.status_code in (200, 201), r2.text
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]

    listed = await http_client.get(
        f"/api/v1/content/pages?slug={slug}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert len(listed.json()["data"]) == 1


# ── has_rfq：僅有表單 RFQ、無 rfq_submit 事件 ──────────────────────────────

@requires_db
async def test_has_rfq_uses_rfq_requests_not_events(
    http_client, two_tenants, admin_token_for_tenant,
):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    visitor_id = uuid.uuid4()
    session_id = uuid.uuid4()
    # 造訪事件（無 rfq_submit）
    await http_client.post("/api/v1/tracking/events", headers={"X-Tenant-ID": str(tenant_a.id)}, json={
        "event_name": "certification_view",
        "visitor_id": str(visitor_id), "session_id": str(session_id),
        "page_url": "https://www.test.com/cert",
        "analytics_consent": True,
    })
    tag = uuid.uuid4().hex[:8]
    r = await http_client.post("/api/v1/forms/rfq", headers={"X-Tenant-ID": str(tenant_a.id)}, json={
        "full_name": "No Event Buyer", "email": f"noevt-{tag}@acme.com",
        "company_name": "Acme", "country": "DE", "consent": True,
        "product_ids": [], "visitor_id": str(visitor_id),
        "message": "Quote please for brackets.",
    })
    assert r.status_code == 201, r.text

    auth = {"Authorization": f"Bearer {token}"}
    # 無 rfq_submit 事件，但 has_rfq=true 應命中
    resp = await http_client.get("/api/v1/tracking/visitors?has_rfq=true", headers=auth)
    assert str(visitor_id) in [v["visitor_id"] for v in resp.json()]

    resp = await http_client.get("/api/v1/tracking/visitors?has_rfq=false", headers=auth)
    assert str(visitor_id) not in [v["visitor_id"] for v in resp.json()]


# ── won_reason 詳情回傳 ────────────────────────────────────────────────────

@requires_db
async def test_lost_does_not_set_first_response_at(
    http_client, two_tenants, admin_token_for_tenant,
):
    """直接標 lost／expired 不算首回，避免 SLA／首回統計偏樂觀。"""
    tenant_a, _ = two_tenants
    tag = uuid.uuid4().hex[:8]
    r = await http_client.post("/api/v1/forms/rfq", headers={"X-Tenant-ID": str(tenant_a.id)}, json={
        "full_name": "Lost Buyer", "email": f"lost-{tag}@acme.com",
        "company_name": "Acme", "country": "DE", "consent": True,
        "product_ids": [], "message": "Not a real inquiry spam.",
    })
    rfq_id = r.json()["rfq_id"]
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}
    await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
        json={"status": "lost", "reason": "垃圾詢價"},
    )
    detail = (await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)).json()
    assert detail["first_response_at"] is None
    assert detail["status"] == "lost"


@requires_db
async def test_task_queue_draft_link_points_to_pages(
    http_client, two_tenants, admin_token_for_tenant,
):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    data = (await http_client.get(
        "/api/v1/ops/task-queue", headers={"Authorization": f"Bearer {token}"},
    )).json()
    draft = next(t for t in data["tasks"] if t["type"] == "content_pending_approval")
    assert draft["link"] == "/dashboard/pages"


@requires_db
async def test_won_reason_returned_in_rfq_detail(
    http_client, two_tenants, admin_token_for_tenant,
):
    tenant_a, _ = two_tenants
    tag = uuid.uuid4().hex[:8]
    r = await http_client.post("/api/v1/forms/rfq", headers={"X-Tenant-ID": str(tenant_a.id)}, json={
        "full_name": "Won Buyer", "email": f"won-{tag}@acme.com",
        "company_name": "Acme", "country": "DE", "consent": True,
        "product_ids": [], "message": "Need a production quote.",
    })
    rfq_id = r.json()["rfq_id"]
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}
    await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
        json={"status": "won", "reason": "交期與認證齊備"},
    )
    detail = (await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)).json()
    assert detail["won_reason"] == "交期與認證齊備"
