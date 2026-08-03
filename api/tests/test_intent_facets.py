"""
Phase 3「看懂買家」驗收測試（實效計畫 §4）

涵蓋：
- Intent Score 2.0 facets（§4.1）：映射、累積、「為何 Hot」解釋
- Admin facet 篩選（§4.5）：facet_min + has_rfq
- facet→CTA（§4.2）：覆寫規則
- AI Advisor 可詢價需求（§4.3）：slots、摘要
- 信任內容標準（§4.4）：certification/capability/case checklist
- facet→CTA→RFQ 路徑事件鏈（§4.5）
"""
import uuid
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from tests.conftest import requires_db

from app.services.intent_facets import (
    FACET_PROCUREMENT_READINESS,
    FACET_PRODUCT_INTEREST,
    FACET_TRUST_VALIDATION,
    FACET_URGENCY,
    apply_event_to_visitor,
    build_intent_explanation,
    facet_for_event,
)
from app.services.dynamic_cta import select_dynamic_cta
from app.services.chat_policy import resolve_dialogue_state, summarize_quotable_needs
from app.services.trust_content_standards import evaluate_trust_content


# ── Facet 映射（免 DB）──────────────────────────────────────────────────────

def test_facet_mapping_by_event_name():
    assert facet_for_event("product_view") == FACET_PRODUCT_INTEREST
    assert facet_for_event("certification_view") == FACET_TRUST_VALIDATION
    assert facet_for_event("spec_download") == FACET_PROCUREMENT_READINESS
    assert facet_for_event("return_visit") == FACET_URGENCY
    assert facet_for_event("unknown_event") is None


def test_facet_mapping_page_view_by_page_type():
    assert facet_for_event("page_view", "certification") == FACET_TRUST_VALIDATION
    assert facet_for_event("page_view", "capability") == FACET_TRUST_VALIDATION
    assert facet_for_event("page_view", "product") == FACET_PRODUCT_INTEREST
    assert facet_for_event("page_view", "blog") is None


def test_apply_event_to_visitor_accumulates():
    visitor = SimpleNamespace(
        facet_product_interest=0, facet_trust_validation=0,
        facet_procurement_readiness=0, facet_urgency=0,
    )
    apply_event_to_visitor(visitor, "certification_view", 3)
    apply_event_to_visitor(visitor, "certification_view", 3)
    apply_event_to_visitor(visitor, "spec_download", 8)
    apply_event_to_visitor(visitor, "return_visit", 6)
    assert visitor.facet_trust_validation == 6
    assert visitor.facet_procurement_readiness == 8
    assert visitor.facet_urgency == 6
    assert visitor.facet_product_interest == 0


def test_explanation_phrases():
    now = datetime.utcnow()
    events = [
        SimpleNamespace(event_name="certification_view", page_type=None, created_at=now - timedelta(hours=2)),
        SimpleNamespace(event_name="certification_view", page_type=None, created_at=now - timedelta(hours=5)),
        SimpleNamespace(event_name="certification_view", page_type=None, created_at=now - timedelta(hours=20)),
        SimpleNamespace(event_name="spec_download", page_type=None, created_at=now - timedelta(hours=30)),
        SimpleNamespace(event_name="rfq_start", page_type=None, created_at=now - timedelta(hours=1)),
    ]
    text = build_intent_explanation(events, now=now)
    assert "48h 內 3 次認證／產能頁" in text
    assert "下載規格表" in text
    assert "進 RFQ 未送出" in text


def test_explanation_rfq_submitted():
    now = datetime.utcnow()
    events = [
        SimpleNamespace(event_name="rfq_start", page_type=None, created_at=now),
        SimpleNamespace(event_name="rfq_submit", page_type=None, created_at=now),
    ]
    text = build_intent_explanation(events, now=now)
    assert "已送出 RFQ" in text
    assert "未送出" not in text


def test_explanation_has_rfq_record_without_submit_event():
    """表單建 RFQ 無 rfq_submit 事件時，仍應顯示已送出（與 has_rfq 一致）。"""
    now = datetime.utcnow()
    events = [
        SimpleNamespace(event_name="rfq_start", page_type=None, created_at=now),
        SimpleNamespace(event_name="spec_download", page_type=None, created_at=now),
    ]
    text = build_intent_explanation(events, now=now, has_rfq_record=True)
    assert "已送出 RFQ" in text
    assert "未送出" not in text


# ── facet→CTA（免 DB）───────────────────────────────────────────────────────

def _ctas():
    return [
        {"id": "1", "action_type": "rfq"},
        {"id": "2", "action_type": "download"},
        {"id": "3", "action_type": "comparison"},
        {"id": "4", "action_type": "contact"},
    ]


def test_cta_procurement_ready_prefers_rfq():
    facets = {FACET_PROCUREMENT_READINESS: 20, FACET_PRODUCT_INTEREST: 5, FACET_TRUST_VALIDATION: 30}
    result = select_dynamic_cta("warm", 20, _ctas(), facets=facets)
    assert result["cta"]["action_type"] == "rfq"
    assert result["personalization"]["facet_reason"] == "procurement_ready"


def test_cta_trust_gap_prefers_download():
    facets = {FACET_PRODUCT_INTEREST: 25, FACET_TRUST_VALIDATION: 5, FACET_PROCUREMENT_READINESS: 0}
    result = select_dynamic_cta("warm", 20, _ctas(), facets=facets)
    assert result["cta"]["action_type"] == "download"
    assert result["personalization"]["facet_reason"] == "trust_gap"


def test_cta_deepen_product_prefers_comparison():
    facets = {FACET_PRODUCT_INTEREST: 25, FACET_TRUST_VALIDATION: 20, FACET_PROCUREMENT_READINESS: 0}
    result = select_dynamic_cta("warm", 20, _ctas(), facets=facets)
    assert result["cta"]["action_type"] == "comparison"


def test_cta_no_facets_falls_back_to_stage():
    result = select_dynamic_cta("hot", 40, _ctas(), facets=None)
    assert result["cta"]["action_type"] == "rfq"


# ── Advisor 可詢價需求（免 DB）──────────────────────────────────────────────

def test_summarize_extracts_quantity_and_missing():
    summary = summarize_quotable_needs(
        "We need 500 pcs of torque wrenches for our assembly line, CE required for Germany."
    )
    assert summary["quantity_known"] is True
    assert summary["quantity_hint"] is not None
    assert summary["use_case_known"] is True
    assert summary["market_requirement"] != "unknown"
    assert "lead_time" in summary["missing"]
    assert "quantity" not in summary["missing"]
    assert "500" in summary["summary_text"]


def test_summarize_empty_marks_all_missing():
    summary = summarize_quotable_needs("hello, tell me about your company")
    assert set(summary["missing"]) == {"quantity", "use_case", "spec_detail", "lead_time"}


def test_high_intent_asks_use_case_first():
    state = resolve_dialogue_state(
        user_question="I need 1000 pcs, please quote",
        context_entity_type="product",
        recent_messages=[],
    )
    assert state.buyer_intent == "high"
    assert state.slots.quantity_known is True
    assert state.missing_slot == "use_case"


def test_high_intent_progresses_through_slots():
    state = resolve_dialogue_state(
        user_question="1000 pcs for automotive assembly, chrome vanadium, DIN standard, deliver in 6 weeks, quote please",
        context_entity_type="product",
        recent_messages=[],
    )
    assert state.buyer_intent == "high"
    assert state.slots.use_case_known is True
    assert state.slots.spec_known is True
    assert state.slots.lead_time_known is True
    assert state.missing_slot is None
    assert state.stage == "rfq_ready"


# ── 信任內容標準（免 DB）────────────────────────────────────────────────────

def test_trust_certification_full_marks():
    body = (
        '<p>Our ISO 9001 certification is issued by SGS, valid until 2027-05. '
        '<a href="https://cdn.example.com/iso9001.pdf">Download certificate</a></p>'
    )
    result = evaluate_trust_content("certification", "ISO 9001 Certificate", body)
    assert result["applicable"] is True
    assert result["score"] == 100


def test_trust_certification_logo_only_fails():
    result = evaluate_trust_content("certification", "Certifications", "<p>We are ISO certified. Quality first.</p>")
    assert result["score"] < 100
    failed = {c["key"] for c in result["checklist"] if not c["passed"]}
    assert "cert_download" in failed
    assert "expiry_marked" in failed


def test_trust_capability_needs_numbers_and_equipment():
    weak = evaluate_trust_content("capability", "Our Factory", "<p>We have great capacity and quality.</p>")
    assert weak["score"] == 0
    strong = evaluate_trust_content(
        "capability",
        "Factory Tour",
        "<p>Monthly capacity 200,000 pcs across 12 CNC machines and 3 production lines, "
        "with 500 sqm warehouse, hardness tester and CMM inspection.</p>",
    )
    assert strong["score"] == 100


def test_trust_case_study_narrative():
    body = "<p>A Germany automotive client faced torque consistency problems; we solved it and reduced defects by 30%.</p>"
    result = evaluate_trust_content("case_study", "Case Study", body)
    assert result["score"] == 100


def test_trust_non_applicable_type():
    result = evaluate_trust_content("blog_post", "Blog", "<p>hello</p>")
    assert result["applicable"] is False


# ── DB 整合：facet 累積＋篩選＋路徑事件鏈（§4.5）───────────────────────────

async def _send_event(client, tenant_id, visitor_id, event_name, page_type=None, session_id=None):
    payload = {
        "event_name": event_name,
        "visitor_id": str(visitor_id),
        "session_id": str(session_id or uuid.uuid4()),
        "page_url": "https://www.test.com/x",
        "page_type": page_type,
    }
    resp = await client.post("/api/v1/tracking/events", json=payload, headers={"X-Tenant-ID": str(tenant_id)})
    assert resp.status_code in (200, 201, 202), resp.text
    return resp


@requires_db
@pytest.mark.asyncio
async def test_facet_cta_rfq_path_end_to_end(http_client, two_tenants, admin_token_for_tenant):
    """§4.5 驗收：至少一條「facet → CTA → RFQ」路徑有事件與轉換紀錄。"""
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    visitor_id = uuid.uuid4()
    session_id = uuid.uuid4()

    # 信任驗證階段：3 次認證頁
    for _ in range(3):
        await _send_event(http_client, tenant_a.id, visitor_id, "certification_view", session_id=session_id)
    # 採購準備：下載規格表 → CTA 點擊
    await _send_event(http_client, tenant_a.id, visitor_id, "spec_download", session_id=session_id)
    await _send_event(http_client, tenant_a.id, visitor_id, "cta_click", session_id=session_id)
    # 轉換：RFQ start → submit
    await _send_event(http_client, tenant_a.id, visitor_id, "rfq_start", session_id=session_id)
    await _send_event(http_client, tenant_a.id, visitor_id, "rfq_submit", session_id=session_id)

    # facet 篩選：信任驗證高
    resp = await http_client.get(
        "/api/v1/tracking/visitors?facet=trust_validation&facet_min=5",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    rows = [r for r in resp.json() if r["visitor_id"] == str(visitor_id)]
    assert len(rows) == 1
    assert rows[0]["facets"]["trust_validation"] >= 9
    assert rows[0]["facets"]["procurement_readiness"] >= 8

    # 「為何 Hot」解釋字串
    assert rows[0]["intent_explanation"]

    # 表單建立 RFQ（不一定有 rfq_submit 事件）→ has_rfq 以 rfq_requests 為準
    tag = uuid.uuid4().hex[:8]
    rfq_resp = await http_client.post(
        "/api/v1/forms/rfq",
        headers={"X-Tenant-ID": str(tenant_a.id)},
        json={
            "full_name": "Facet Buyer", "email": f"facet-{tag}@acme.com",
            "company_name": "Acme", "country": "DE", "consent": True,
            "product_ids": [], "visitor_id": str(visitor_id),
            "message": "Need quote for stamped parts.",
        },
    )
    assert rfq_resp.status_code == 201, rfq_resp.text

    resp = await http_client.get(
        "/api/v1/tracking/visitors?facet=trust_validation&facet_min=5&has_rfq=false",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids = [r["visitor_id"] for r in resp.json()]
    assert str(visitor_id) not in ids

    resp = await http_client.get(
        "/api/v1/tracking/visitors?has_rfq=true",
        headers={"Authorization": f"Bearer {token}"},
    )
    ids = [r["visitor_id"] for r in resp.json()]
    assert str(visitor_id) in ids

    # 事件鏈完整（facet → CTA → RFQ）
    resp = await http_client.get(
        f"/api/v1/tracking/visitors/{visitor_id}/events",
        headers={"Authorization": f"Bearer {token}"},
    )
    chain = [e["event_name"] for e in resp.json()]
    for expected in ("certification_view", "spec_download", "cta_click", "rfq_start", "rfq_submit"):
        assert expected in chain


@requires_db
@pytest.mark.asyncio
async def test_trust_check_endpoint(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, tenant_b = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    headers = {"Authorization": f"Bearer {token}"}
    slug = f"cert-{uuid.uuid4().hex[:8]}"

    resp = await http_client.post(
        "/api/v1/content/pages",
        json={
            "page_type": "certification",
            "slug": slug,
            "title": "ISO 9001 by SGS",
            "body": '<p>Issued by SGS, valid until 2027-05. <a href="https://cdn.example.com/c.pdf">Download certificate</a></p>',
            "locale": "en",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    page_id = resp.json()["data"]["id"]

    resp = await http_client.get(f"/api/v1/content/pages/{page_id}/trust-check", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["applicable"] is True
    assert data["score"] == 100

    # 跨租戶 → 404
    token_b = await admin_token_for_tenant(tenant_b.id)
    resp = await http_client.get(
        f"/api/v1/content/pages/{page_id}/trust-check",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
