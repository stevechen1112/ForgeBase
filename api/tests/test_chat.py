import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.chat import ChatMessageCreate, ChatSessionCreate
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


@requires_db
@pytest.mark.asyncio
async def test_chat_session_create_auto_bootstraps_tracking_context():
    payload = {
        "visitor_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "context_page": "/faq",
        "context_entity_type": "faq",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/chat/sessions", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["chat_session_id"]
    assert body["data"]["greeting"]
    assert len(body["data"]["suggestions"]) == 3