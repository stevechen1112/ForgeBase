"""Phase 4「成果與閉環」：狀態機延伸、回覆品質輔助、成果儀表板、漏斗、任務佇列。

驗收依據（實效計畫）：
- §6.3 成交／流失原因必填；漏斗各層轉化率可查
- §5.4 回覆前 checklist＋Quote Readiness＋範本庫
- §6.1 客戶首屏五項；§6.2 至少一篇內容可回溯到 RFQ
- §7.1 顧問一個入口能清「今日必處理」
"""
import uuid

from app.services.reply_quality import (
    build_reply_checklist,
    match_templates,
    quote_readiness,
    suggested_questions,
)
from tests.conftest import requires_db


# ── 回覆品質輔助單元測試（免 DB）───────────────────────────────────────────

class _RfqStub:
    def __init__(self, **kw):
        self.form_data = kw.get("form_data")
        self.incoterm = kw.get("incoterm")
        self.annual_volume = kw.get("annual_volume")
        self.required_certs_json = kw.get("required_certs_json")


def test_checklist_flags_gaps_and_questions():
    rfq = _RfqStub(form_data='{"quantity": "", "specifications": "", "message": "pls quote"}')
    checklist = build_reply_checklist(rfq)
    assert all({"key", "label", "ok", "ask"} <= set(item) for item in checklist)
    gaps = [i for i in checklist if not i["ok"]]
    assert len(gaps) >= 4  # 規格／圖面／包裝／認證／Incoterms／量 全缺
    questions = suggested_questions(rfq)
    assert 1 <= len(questions) <= 4
    assert all(q.endswith("?") for q in questions)


def test_quote_readiness_ready_when_complete():
    rfq = _RfqStub(
        form_data='{"quantity": "10k pcs", "specifications": "SUS304 per drawing, pallet packaging", "message": "drawing attached"}',
        incoterm="FOB",
        annual_volume="120k",
        required_certs_json='["CE"]',
    )
    readiness = quote_readiness(rfq)
    assert readiness["ready"] is True
    assert readiness["score"] == 100
    assert readiness["gaps"] == []


def test_template_matching_country_first():
    from app.models.reply_template import ReplyTemplate
    generic = ReplyTemplate(name="generic", body="g", locale="en")
    germany = ReplyTemplate(name="de", body="d", country="DE", locale="en")
    france = ReplyTemplate(name="fr", body="f", country="FR", locale="en")
    ranked = match_templates([generic, france, germany], country="DE")
    assert ranked[0].name == "de"
    assert ranked[-1].name == "fr"  # 他國範本墊底


# ── DB 整合測試 ────────────────────────────────────────────────────────────

async def _create_rfq(http_client, tenant_id, **overrides):
    tag = uuid.uuid4().hex[:8]
    payload = {
        "full_name": "Buyer", "email": f"p4-{tag}@acme.com",
        "company_name": "Acme", "country": "DE", "consent": True,
        "product_ids": [],
        "specifications": "SUS304, tolerance +/-0.05mm",
        "quantity": "10,000 pcs", "incoterm": "FOB",
        "required_certs": ["CE"],
    }
    payload.update(overrides)
    r = await http_client.post(
        "/api/v1/forms/rfq", headers={"X-Tenant-ID": str(tenant_id)}, json=payload,
    )
    assert r.status_code == 201, r.text
    return r.json()["rfq_id"]


@requires_db
async def test_status_reason_required_and_negotiation(http_client, two_tenants, admin_token_for_tenant):
    """§6.3：won/lost 必須附原因；negotiation 為合法狀態；quoted 自動記 quote_sent_at。"""
    tenant_a, _ = two_tenants
    rfq_id = await _create_rfq(http_client, tenant_a.id)
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}

    # negotiation 合法
    r = await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth, json={"status": "negotiation"})
    assert r.status_code == 200, r.text

    # quoted → quote_sent_at 自動記錄
    r = await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth, json={"status": "quoted"})
    assert r.status_code == 200, r.text
    detail = (await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}", headers=auth)).json()
    assert detail["quote_sent_at"] is not None

    # won 無原因 → 422
    r = await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth, json={"status": "won"})
    assert r.status_code == 422

    # won 附原因 → 通過且寫入 won_reason
    r = await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
        json={"status": "won", "reason": "價格與交期具競爭力"},
    )
    assert r.status_code == 200, r.text

    # lost 無原因 → 422（驗證 lost 同規則）
    rfq2 = await _create_rfq(http_client, tenant_a.id)
    r = await http_client.put(f"/api/v1/tracking/rfqs/{rfq2}/status", headers=auth, json={"status": "lost"})
    assert r.status_code == 422
    r = await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq2}/status", headers=auth,
        json={"status": "lost", "reason": "報價高於對手 15%"},
    )
    assert r.status_code == 200, r.text


@requires_db
async def test_templates_crud_and_tenant_isolation(http_client, two_tenants, admin_token_for_tenant):
    """§5.4 範本庫：CRUD 正常，跨租戶不可見。"""
    tenant_a, tenant_b = two_tenants
    token_a = await admin_token_for_tenant(tenant_a.id)
    token_b = await admin_token_for_tenant(tenant_b.id)
    auth_a = {"Authorization": f"Bearer {token_a}"}
    auth_b = {"Authorization": f"Bearer {token_b}"}

    r = await http_client.post(
        "/api/v1/tracking/rfqs/templates", headers=auth_a,
        json={"name": "DE 五金報價", "body": "Dear {name}, ...", "country": "DE", "locale": "en"},
    )
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    listed = (await http_client.get("/api/v1/tracking/rfqs/templates", headers=auth_a)).json()
    assert any(t["id"] == tid for t in listed)

    # B 租戶不可見、不可改
    listed_b = (await http_client.get("/api/v1/tracking/rfqs/templates", headers=auth_b)).json()
    assert all(t["id"] != tid for t in listed_b)
    r = await http_client.patch(
        f"/api/v1/tracking/rfqs/templates/{tid}", headers=auth_b, json={"name": "hijack"},
    )
    assert r.status_code == 404

    # 本人可改可刪
    r = await http_client.patch(
        f"/api/v1/tracking/rfqs/templates/{tid}", headers=auth_a, json={"body": "updated"},
    )
    assert r.status_code == 200 and r.json()["body"] == "updated"
    r = await http_client.delete(f"/api/v1/tracking/rfqs/templates/{tid}", headers=auth_a)
    assert r.status_code == 204


@requires_db
async def test_reply_assist_endpoint(http_client, two_tenants, admin_token_for_tenant):
    """§5.4：reply-assist 回傳 checklist／readiness／建議反問／匹配範本。"""
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}
    await http_client.post(
        "/api/v1/tracking/rfqs/templates", headers=auth,
        json={"name": "DE template", "body": "Dear buyer...", "country": "DE"},
    )
    rfq_id = await _create_rfq(http_client, tenant_a.id)

    r = await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}/reply-assist", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert len(data["checklist"]) == 6
    assert 0 <= data["quote_readiness"]["score"] <= 100
    assert data["buyer_country"] == "DE"
    assert data["templates"] and data["templates"][0]["country"] == "DE"


@requires_db
async def test_outcomes_five_items_and_attribution(http_client, two_tenants, admin_token_for_tenant):
    """§6.1 首屏五項齊全；§6.2 source_page 可回溯到 RFQ。"""
    tenant_a, _ = two_tenants
    source = f"/en/blog/stamping-guide-{uuid.uuid4().hex[:6]}"
    rfq_id = await _create_rfq(http_client, tenant_a.id, source_page=source)
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}
    # 觸發首回，讓 first_response 有資料
    await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth, json={"status": "assigned"})

    r = await http_client.get("/api/v1/tracking/outcomes", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert {"qualified_rfq", "first_response", "funnel_status", "top_source_pages", "next_week_suggestions"} <= set(data)
    assert 1 <= len(data["next_week_suggestions"]) <= 3
    # §6.4：至少一篇內容可回溯到 RFQ
    assert any(s["source_page"] == source for s in data["top_source_pages"])


@requires_db
async def test_funnel_layers_and_conversion(http_client, two_tenants, admin_token_for_tenant):
    """§6.3：漏斗七層齊全，各層轉化率可查。"""
    tenant_a, _ = two_tenants
    rfq_id = await _create_rfq(http_client, tenant_a.id)
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}
    await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth, json={"status": "quoted"})

    r = await http_client.get("/api/v1/tracking/funnel?days=30", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    layers = {l["layer"]: l for l in data["layers"]}
    assert list(layers) == ["traffic", "high_intent", "rfq", "qualified_rfq", "quoted", "negotiation", "won"]
    assert layers["rfq"]["count"] >= 1
    assert layers["quoted"]["count"] >= 1
    assert layers["rfq"]["conversion_from_prev_pct"] is None
    assert layers["traffic"]["cohort"] == "visitor"
    assert layers["rfq"]["cohort"] == "rfq"
    assert all(
        layer["conversion_from_prev_pct"] is None
        or 0 <= layer["conversion_from_prev_pct"] <= 100
        for layer in layers.values()
    )
    # negotiation 層必須套用 days 視窗（本測試剛建立的 quoted 不應算進 negotiation）
    assert layers["negotiation"]["count"] == 0


@requires_db
async def test_task_queue_aggregates(http_client, two_tenants, admin_token_for_tenant):
    """§7.1：任務佇列含 SLA 逾期／低品質／草稿等類型，顧問一個入口可清。"""
    tenant_a, _ = two_tenants
    # 低品質 RFQ（免費信箱＋一句話）
    await _create_rfq(
        http_client, tenant_a.id,
        email=f"low-{uuid.uuid4().hex[:6]}@gmail.com", message="pls send catalog",
        specifications=None, quantity=None, incoterm=None, required_certs=[],
    )
    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}

    r = await http_client.get("/api/v1/ops/task-queue", headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    types = {t["type"] for t in data["tasks"]}
    assert {"sla_breached_rfq", "rfq_follow_up_due", "hot_visitor_unassigned", "low_quality_rfq",
            "content_pending_approval", "verification_anomaly"} == types
    follow_up = next(t for t in data["tasks"] if t["type"] == "rfq_follow_up_due")
    assert follow_up["link"] == "/dashboard/rfqs?follow_up=due"
    low = next(t for t in data["tasks"] if t["type"] == "low_quality_rfq")
    assert low["count"] >= 1
    anomaly = next(t for t in data["tasks"] if t["type"] == "verification_anomaly")
    assert anomaly["available"] is False  # 誠實標記：待 CF 串接
