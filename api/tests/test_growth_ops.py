"""Website-to-RFQ handoff helpers and operational queue contracts."""

import uuid

from app.services.reply_quality import build_reply_checklist, match_templates, quote_readiness, suggested_questions
from tests.conftest import requires_db


class _RfqStub:
    def __init__(self, **values):
        self.form_data = values.get("form_data")
        self.incoterm = values.get("incoterm")
        self.annual_volume = values.get("annual_volume")
        self.required_certs_json = values.get("required_certs_json")


def test_reply_checklist_exposes_missing_raw_requirements():
    rfq = _RfqStub(form_data='{"quantity":"","specifications":"","message":"please review"}')
    checklist = build_reply_checklist(rfq)
    assert all({"key", "label", "ok", "ask"} <= set(item) for item in checklist)
    assert len([item for item in checklist if not item["ok"]]) >= 4
    assert all(question.endswith("?") for question in suggested_questions(rfq))


def test_quote_readiness_is_reply_preparation_not_buyer_score():
    rfq = _RfqStub(
        form_data='{"quantity":"10k pcs","specifications":"SUS304 per drawing, pallet packaging","message":"drawing attached"}',
        incoterm="FOB", annual_volume="120k", required_certs_json='["CE"]',
    )
    readiness = quote_readiness(rfq)
    assert readiness["ready"] is True
    assert readiness["score"] == 100
    assert readiness["gaps"] == []


def test_reply_template_matching_prefers_buyer_country():
    from app.models.reply_template import ReplyTemplate
    generic = ReplyTemplate(name="generic", body="g", locale="en")
    germany = ReplyTemplate(name="de", body="d", country="DE", locale="en")
    france = ReplyTemplate(name="fr", body="f", country="FR", locale="en")
    ranked = match_templates([generic, france, germany], country="DE")
    assert ranked[0].name == "de"
    assert ranked[-1].name == "fr"


async def _create_rfq(http_client, tenant_id):
    response = await http_client.post(
        "/api/v1/forms/rfq", headers={"X-Tenant-ID": str(tenant_id)},
        json={"full_name": "Buyer", "email": f"handoff-{uuid.uuid4().hex[:8]}@acme.com", "company_name": "Acme", "country": "DE", "consent": True, "product_ids": [], "specifications": "SUS304 per drawing", "quantity": "10,000 pcs", "incoterm": "FOB", "required_certs": ["CE"]},
    )
    assert response.status_code == 201, response.text
    return response.json()["rfq_id"]


@requires_db
async def test_retired_sales_statuses_and_endpoints_are_gone(http_client, two_tenants, admin_token_for_tenant):
    tenant, _ = two_tenants
    rfq_id = await _create_rfq(http_client, tenant.id)
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant.id)}"}
    for status in ("in_progress", "quoted", "negotiation", "won", "lost", "expired"):
        response = await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth, json={"status": status})
        assert response.status_code == 422
    assert (await http_client.get("/api/v1/tracking/outcomes", headers=auth)).status_code == 404
    assert (await http_client.get("/api/v1/tracking/funnel", headers=auth)).status_code == 404
    assert (await http_client.get("/api/v1/tracking/analytics/funnel", headers=auth)).status_code == 404
    assert (await http_client.put(f"/api/v1/tracking/rfqs/{rfq_id}/follow-up", headers=auth, json={})).status_code == 404


@requires_db
async def test_reply_assist_and_task_queue_remain_operational(http_client, two_tenants, admin_token_for_tenant):
    tenant, _ = two_tenants
    rfq_id = await _create_rfq(http_client, tenant.id)
    auth = {"Authorization": f"Bearer {await admin_token_for_tenant(tenant.id)}"}
    assist = await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}/reply-assist", headers=auth)
    assert assist.status_code == 200
    assert {"checklist", "quote_readiness", "suggested_questions", "templates"} <= set(assist.json())
    queue = await http_client.get("/api/v1/ops/task-queue", headers=auth)
    assert queue.status_code == 200
    tasks = {item["type"]: item for item in queue.json()["tasks"]}
    assert set(tasks) == {"rfq_unassigned", "rfq_awaiting_acceptance", "content_pending_approval"}
    assert tasks["rfq_unassigned"]["count"] >= 1
    assert tasks["rfq_unassigned"]["link"] == "/dashboard/rfqs?attention=unassigned"
