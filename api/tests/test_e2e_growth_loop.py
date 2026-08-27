"""Phase 5：E2E 成長迴路＋跨租戶污染測試（實效計畫 §8.1）。

一條完整迴路：
內容頁存在 → 訪客事件累積 facets → 送 RFQ（帶 source_page 歸因）→
品質分數／SLA → 狀態機 new→assigned→quoted→negotiation→won(原因) →
outcomes／funnel／attribution／outcome-feedback 全部反映 → 他租戶什麼都看不到。
"""
import uuid

from tests.conftest import requires_db


async def _send_event(client, tenant_id, visitor_id, event_name, page_type=None, session_id=None):
    payload = {
        "event_name": event_name,
        "visitor_id": str(visitor_id),
        "session_id": str(session_id or uuid.uuid4()),
        "page_url": "https://www.test.com/x",
        "page_type": page_type,
        "analytics_consent": True,
    }
    resp = await client.post("/api/v1/tracking/events", json=payload, headers={"X-Tenant-ID": str(tenant_id)})
    assert resp.status_code in (200, 201, 202), resp.text


@requires_db
async def test_full_growth_loop_end_to_end(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token_a}"}
    tag = uuid.uuid4().hex[:8]

    # 1. 內容頁存在（歸因對照目標）
    slug = f"e2e-stamping-guide-{tag}"
    r = await http_client.post("/api/v1/content/pages", headers=auth, json={
        "page_type": "blog_post", "slug": slug, "title": "Stamping Guide",
        "body": "<p>Guide</p>", "locale": "en", "status": "published",
    })
    assert r.status_code == 201, r.text

    # 2. 訪客事件累積 facets（認證頁 → trust；下載規格 → procurement）
    visitor_id = uuid.uuid4()
    session_id = uuid.uuid4()
    for _ in range(3):
        await _send_event(http_client, tenant_a.id, visitor_id, "page_view", page_type="certification", session_id=session_id)
    await _send_event(http_client, tenant_a.id, visitor_id, "spec_download", session_id=session_id)

    v = (await http_client.get(
        f"/api/v1/tracking/visitors/{visitor_id}", headers=auth,
    )).json()
    assert v["facets"]["trust_validation"] >= 3
    assert v["intent_explanation"]

    # 3. 送 RFQ（帶 source_page 歸因到內容頁）
    r = await http_client.post("/api/v1/forms/rfq", headers={"X-Tenant-ID": str(tenant_a.id)}, json={
        "full_name": "E2E Buyer", "email": f"e2e-{tag}@acme-industrial.com",
        "company_name": "Acme Industrial", "country": "DE", "consent": True,
        "job_title": "Procurement Manager",
        "product_ids": [],
        "specifications": "SUS304, tolerance +/-0.05mm, per drawing",
        "quantity": "10,000 pcs", "incoterm": "FOB",
        "annual_volume": "120k pcs", "is_trial_order": False,
        "target_price": "USD 1.20/pc",
        "timeline": "1-3 months",
        "required_certs": ["CE"],
        "message": "Long-term supplier sourcing for stamped brackets.",
        "visitor_id": str(visitor_id),
        "source_page": f"/en/blog/{slug}",
    })
    assert r.status_code == 201, r.text
    rfq_id = r.json()["rfq_id"]

    detail = (await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)).json()
    assert detail["quality_score"] >= 70
    assert detail["sla_due_at"] is not None

    # 4. 狀態機走完銷售流程
    for status, extra in [
        ("assigned", {}),
        ("quoted", {}),
        ("negotiation", {}),
        ("won", {"reason": "價格與交期具競爭力，買家驗廠通過"}),
    ]:
        r = await http_client.put(
            f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
            json={"status": status, **extra},
        )
        assert r.status_code == 200, f"{status}: {r.text}"

    detail = (await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)).json()
    assert detail["first_response_at"] is not None
    assert detail["quote_sent_at"] is not None

    # 5. 成果面全部反映
    outcomes = (await http_client.get("/api/v1/tracking/outcomes", headers=auth)).json()
    assert outcomes["qualified_rfq"]["this_month"] >= 1
    assert any(s["source_page"] == f"/en/blog/{slug}" for s in outcomes["top_source_pages"])

    funnel = (await http_client.get("/api/v1/tracking/funnel?days=30", headers=auth)).json()
    layers = {l["layer"]: l for l in funnel["layers"]}
    assert layers["won"]["count"] >= 1
    assert layers["negotiation"]["count"] >= 1  # 累計到達談判／成交，不因成交而回退

    attribution = (await http_client.get("/api/v1/tracking/attribution/content", headers=auth)).json()
    blog_bucket = next((b for b in attribution["by_page_type"] if b["key"] == "blog_post"), None)
    assert blog_bucket is not None
    assert blog_bucket["rfq"] >= 1 and blog_bucket["won"] >= 1

    feedback = (await http_client.get("/api/v1/tracking/intent/outcome-feedback", headers=auth)).json()
    assert feedback["sample"]["won"] >= 1
    assert "觀察性" in feedback["note"]

    queue = (await http_client.get("/api/v1/ops/task-queue", headers=auth)).json()
    assert queue["total_open"] >= 0  # 端點可用；本迴路 RFQ 已結案不應卡在 SLA 逾期
    assert not any(i.get("rfq_number") == detail["rfq_number"]
                   for t in queue["tasks"] if t["type"] == "sla_breached_rfq" for i in t["items"])

    # 6. 跨租戶污染檢查：tenant B 在所有成果端點都看不到 A 的資料
    token_b = await admin_token_for_tenant(tenant_b.id)
    auth_b = {"Authorization": f"Bearer {token_b}"}

    outcomes_b = (await http_client.get("/api/v1/tracking/outcomes", headers=auth_b)).json()
    assert outcomes_b["qualified_rfq"]["this_month"] == 0
    assert outcomes_b["top_source_pages"] == []

    funnel_b = (await http_client.get("/api/v1/tracking/funnel?days=30", headers=auth_b)).json()
    assert all(l["count"] == 0 for l in funnel_b["layers"])

    attribution_b = (await http_client.get("/api/v1/tracking/attribution/content", headers=auth_b)).json()
    assert attribution_b["rfq_with_source"] == 0

    feedback_b = (await http_client.get("/api/v1/tracking/intent/outcome-feedback", headers=auth_b)).json()
    assert feedback_b["sample"] == 0 or feedback_b["sample"]["won"] == 0

    queue_b = (await http_client.get("/api/v1/ops/task-queue", headers=auth_b)).json()
    sla_b = next(t for t in queue_b["tasks"] if t["type"] == "sla_breached_rfq")
    assert sla_b["count"] == 0

    r = await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}/reply-assist", headers=auth_b)
    assert r.status_code == 404
