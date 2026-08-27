import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.assets import _validate_file_signature
from app.api.v1.endpoints.events import EventIn
from app.api.v1.endpoints.rfqs import RFQFormIn
from app.core.locale import infer_message_locale, normalize_locale, to_content_locale
from app.services.chat_locale import fallback_reply, localized_greeting, localized_suggestions
from app.services.chat_policy import build_response_plan
from tests.conftest import _make_engine, requires_db


def test_locale_normalization_keeps_route_and_cms_forms_distinct():
    assert normalize_locale("zh_tw") == "zh-TW"
    assert to_content_locale("zh-TW") == "zh-tw"
    assert infer_message_locale("你好，我想詢價", "en") == "zh-TW"


def test_chinese_chat_copy_and_policy_question():
    assert "材質" in localized_greeting("product", "NF-100", "zh-TW")
    assert localized_suggestions("home", "zh-TW")[0].startswith("哪個")
    assert "目前沒有足夠" in fallback_reply("zh-TW")
    plan = build_response_plan(
        user_question="我想詢價",
        context_entity_type="product",
        recent_messages=[],
        model_suggested_action="none",
        model_needs_clarification=False,
        model_clarifying_question=None,
        locale="zh-TW",
    )
    assert plan.suggested_action == "rfq"
    assert plan.clarifying_question
    assert "數量" in plan.clarifying_question


def test_asset_signature_validation_rejects_spoofed_pdf_and_binary():
    with pytest.raises(HTTPException) as pdf_error:
        _validate_file_signature("manual.pdf", "application/pdf", b"MZ executable")
    assert pdf_error.value.status_code == 415
    with pytest.raises(HTTPException):
        _validate_file_signature("payload.exe", "application/octet-stream", b"MZ")
    _validate_file_signature("drawing.step", "application/octet-stream", b"ISO-10303-21;")


def test_tracking_event_requires_explicit_consent_declaration():
    implicit = EventIn(event_name="page_view", visitor_id=uuid.uuid4())
    explicit = EventIn(event_name="page_view", visitor_id=uuid.uuid4(), analytics_consent=True)
    assert implicit.analytics_consent is False
    assert explicit.analytics_consent is True


def test_rfq_input_bounds_and_mutable_defaults_are_isolated():
    base = {
        "full_name": "Buyer Name",
        "email": "buyer@example.com",
        "company_name": "Buyer Company",
        "country": "TW",
        "consent": True,
    }
    first = RFQFormIn(**base)
    second = RFQFormIn(**base)
    first.product_ids.append(str(uuid.uuid4()))
    assert second.product_ids == []
    with pytest.raises(ValidationError):
        RFQFormIn(**base, message="x" * 4001)


@requires_db
async def test_rfq_accepts_session_identity_without_analytics_record(http_client, two_tenants):
    """Declining analytics must not prevent the essential RFQ workflow."""
    tenant, _ = two_tenants
    response = await http_client.post(
        "/api/v1/forms/rfq",
        headers={"X-Tenant-ID": str(tenant.id)},
        json={
            "full_name": "Privacy Buyer",
            "email": f"privacy-{uuid.uuid4().hex[:8]}@example.com",
            "company_name": "Privacy Tools GmbH",
            "country": "DE",
            "visitor_id": str(uuid.uuid4()),
            "consent": True,
        },
    )
    assert response.status_code == 201, response.text


@requires_db
async def test_chat_handoff_draft_is_consumed_once_under_concurrency(http_client, two_tenants):
    tenant, _ = two_tenants
    headers = {"X-Tenant-ID": str(tenant.id)}
    visitor_id = uuid.uuid4()
    chat = await http_client.post(
        "/api/v1/chat/sessions",
        headers=headers,
        json={
            "visitor_id": str(visitor_id),
            "context_entity_type": "home",
            "locale": "en",
        },
    )
    assert chat.status_code == 201, chat.text
    chat_id = chat.json()["data"]["chat_session_id"]
    handoff = await http_client.post(
        f"/api/v1/chat/sessions/{chat_id}/handoff",
        headers=headers,
        json={"visitor_id": str(visitor_id), "intent_reason": "rfq", "prefill": {}},
    )
    assert handoff.status_code == 200, handoff.text
    draft_id = handoff.json()["data"]["draft_id"]

    def payload(email: str) -> dict:
        return {
            "full_name": "Concurrent Buyer",
            "email": email,
            "company_name": "Concurrency GmbH",
            "country": "DE",
            "visitor_id": str(visitor_id),
            "draft_id": draft_id,
            "consent": True,
        }

    first, second = await asyncio.gather(
        http_client.post(
            "/api/v1/forms/rfq",
            headers=headers,
            json=payload(f"first-{uuid.uuid4().hex[:8]}@example.com"),
        ),
        http_client.post(
            "/api/v1/forms/rfq",
            headers=headers,
            json=payload(f"second-{uuid.uuid4().hex[:8]}@example.com"),
        ),
    )
    assert sorted([first.status_code, second.status_code]) == [201, 422]


@requires_db
async def test_deferred_auto_reply_releases_worker_without_consuming_retry(
    two_tenants, monkeypatch
):
    from app.models.operational_job import OperationalJob
    from app.services import operational_outbox
    from app.services.rfq_auto_reply import AutoReplyDeferred

    tenant, _ = two_tenants
    engine, factory = _make_engine()

    @asynccontextmanager
    async def session_context():
        async with factory() as session:
            yield session

    monkeypatch.setattr(operational_outbox, "get_session_ctx", session_context)
    execute = AsyncMock(side_effect=AutoReplyDeferred(120))
    monkeypatch.setattr(operational_outbox, "_execute", execute)

    job = OperationalJob(
        tenant_id=tenant.id,
        job_type="rfq_auto_reply",
        payload_json=json.dumps({"rfq_id": str(uuid.uuid4()), "tenant_id": str(tenant.id)}),
        idempotency_key=f"test-deferred-{uuid.uuid4()}",
        available_at=datetime(2000, 1, 1),
    )
    async with factory() as session:
        session.add(job)
        await session.commit()

    stats = await operational_outbox.process_operational_jobs(limit=1)
    assert stats == {"completed": 0, "retried": 1, "failed": 0}
    async with factory() as session:
        saved = await session.get(OperationalJob, job.id)
        assert saved is not None
        assert saved.status == "retry"
        assert saved.attempts == 0
        assert saved.locked_at is None

    await engine.dispose()


@requires_db
async def test_locale_coverage_endpoint_queries_all_supported_content_tables(
    http_client, two_tenants, admin_token_for_tenant
):
    tenant, _ = two_tenants
    token = await admin_token_for_tenant(tenant.id)
    response = await http_client.get(
        "/api/v1/content/locale-coverage?target_locale=en",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["source_locale"] == "zh-tw"
    assert payload["target_locale"] == "en"
    assert {row["entity"] for row in payload["entities"]} == {
        "products",
        "categories",
        "applications",
        "pages",
        "faqs",
        "comparisons",
        "certifications",
        "capabilities",
    }
