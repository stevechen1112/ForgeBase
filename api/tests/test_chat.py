import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.product import Product
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate
from app.services.chat_orchestrator import finalize_generated_chat_response
from app.services.chat_service import (
    ChatService,
    _format_product_snapshot,
    _infer_clarifying_question,
    _merge_reply_and_clarifying_question,
    _strip_html,
)
from app.services.intent_scoring import calculate_score_delta
from tests.conftest import requires_db


def test_chat_session_create_defaults():
    payload = ChatSessionCreate(
        visitor_id=uuid.uuid4(),
        context_page="/faq",
        context_entity_type="faq",
    )
    assert payload.context_entity_type == "faq"
    assert payload.locale == "en"


def test_chat_message_create_rejects_empty_content():
    try:
        ChatMessageCreate(visitor_id=uuid.uuid4(), content="   ")
        assert False, "Expected validation failure"
    except ValueError:
        assert True


def test_chat_intent_scoring_defaults():
    assert calculate_score_delta("chat_start", {}) == 8
    assert calculate_score_delta("chat_rfq_handoff", {}) == 20


@pytest.mark.asyncio
async def test_chat_llm_failure_uses_requested_chinese_locale(monkeypatch):
    def unavailable_client():
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr("app.services.chat_service.get_openai_client", unavailable_client)

    payload = await ChatService(SimpleNamespace())._generate_reply(
        context_page="/zh-TW/products/torque-wrenches/industrial-torque-wrench",
        context_entity_type="product",
        entity_summary="",
        faq_summary="",
        cert_summary="",
        recent_messages=[],
        user_question="你好，請問最低訂購量是多少？",
        locale="zh-TW",
    )

    assert payload["ai_available"] is False
    assert payload["reply"] == (
        "目前沒有足夠且已確認的資料可以直接回答。"
        "最快的下一步是送出詢價，讓業務依您的需求確認。"
    )
    assert "I don't" not in payload["reply"]

def test_strip_html_removes_tags_and_collapses_whitespace():
    assert _strip_html("<p>Hello <strong>world</strong></p>\n<div> test</div>") == "Hello world test"


def test_format_product_snapshot_includes_specs_summary():
    product = Product(
        product_name="Digital Torque Adapter",
        slug="digital-torque-adapter",
        model_number="DTA-120",
        short_description="<p>Digital adapter for retrofit torque verification.</p>",
        full_description=None,
        specifications='[{"name":"Drive","value":"1/2","unit":"in"},{"name":"Torque Range","value":"30-200","unit":"Nm"}]',
        category_id=uuid.uuid4(),
    )

    snapshot = _format_product_snapshot(product)

    assert "Digital Torque Adapter" in snapshot
    assert "model: DTA-120" in snapshot
    assert "summary: Digital adapter for retrofit torque verification." in snapshot
    assert "Drive: 1/2 in" in snapshot
    assert "Torque Range: 30-200 Nm" in snapshot

def test_infer_clarifying_question_for_broad_category_query() -> None:
    question = "Which hand tool assortment should I start with for a new distributor launch?"

    clarifying_question = _infer_clarifying_question(question, "category", "none")

    assert clarifying_question == "Are you evaluating a standard supply range, or an OEM/private-label program"


def test_merge_reply_and_clarifying_question_appends_single_prompt() -> None:
    reply, needs_clarification, clarifying_question = _merge_reply_and_clarifying_question(
        "I can narrow this to 3 practical starter bundles based on your route to market.",
        "Are you targeting a standard supply range or an OEM/private-label program",
    )

    assert needs_clarification is True
    assert clarifying_question == "Are you targeting a standard supply range or an OEM/private-label program?"
    assert "One key question before I narrow this further:" in reply


def test_finalize_generated_chat_response_adds_program_type_clarification_for_broad_category_question() -> None:
    payload = finalize_generated_chat_response(
        user_question="Which hand tool assortment should I start with for a new distributor launch?",
        context_entity_type="category",
        recent_messages=[],
        payload={
            "reply": "I can narrow this to 3 practical starter bundles based on your route to market.",
            "suggested_action": "none",
        },
    )

    assert payload["needs_clarification"] is True
    assert payload["clarifying_question"] == "Are you evaluating a standard supply range, or an OEM/private-label program?"
    assert payload["suggested_action"] == "none"


def test_finalize_generated_chat_response_promotes_rfq_for_oem_question_with_missing_quantity() -> None:
    payload = finalize_generated_chat_response(
        user_question="We need OEM packaging for this range. Which models fit best?",
        context_entity_type="category",
        recent_messages=[],
        payload={
            "reply": "I can shortlist the strongest OEM-fit models from this range.",
            "suggested_action": "none",
        },
    )

    assert payload["suggested_action"] == "rfq"
    assert payload["needs_clarification"] is True
    assert payload["clarifying_question"] == "What estimated quantity or MOQ target should I use for the first RFQ round?"


def test_finalize_generated_chat_response_uses_recent_messages_to_advance_state() -> None:
    recent_messages = [
        SimpleNamespace(role="user", content="This will be an OEM/private-label program with custom packaging."),
        SimpleNamespace(role="assistant", content="Understood."),
    ]
    payload = finalize_generated_chat_response(
        user_question="Before RFQ, what exact details do you still need from us?",
        context_entity_type="application",
        recent_messages=recent_messages,
        payload={
            "reply": "I still need the commercial inputs that determine MOQ and final packaging feasibility.",
            "suggested_action": "none",
        },
    )

    assert payload["suggested_action"] == "rfq"
    assert payload["clarifying_question"] == "What estimated quantity or MOQ target should I use for the first RFQ round?"


@requires_db
@pytest.mark.asyncio
async def test_chat_session_create_auto_bootstraps_tracking_context(http_client):
    payload = {
        "visitor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "context_page": "/faq",
        "context_entity_type": "faq",
    }

    response = await http_client.post("/api/v1/chat/sessions", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["chat_session_id"]
    assert body["data"]["greeting"]
    assert len(body["data"]["suggestions"]) == 3
    assert body["data"]["response_locale"] == "en"
