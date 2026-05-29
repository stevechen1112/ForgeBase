"""
TDD: ForgeBase must auto-trigger AgentOS when an RFQ is created and bind run_id.

These tests WILL FAIL until all of the following are implemented:

  1. RFQRequest model gains:
       agent_run_id: str | None = None
     plus a corresponding Alembic migration.

  2. The RFQ creation handler (POST /api/v1/forms/rfq or POST /tracking/rfqs)
     calls AgentOS POST /tasks after persisting the RFQ, with payload:
       {
         "tenant_id": <tenant_id>,
         "domain": "forgebase_rfq",
         "objective": "Process RFQ <rfq_number>",
         "risk_level": "medium",
         "workflow_input": {
           "rfq_id": "<rfq_number or id>",
           "forgebase_base_url": "<FORGEBASE_API_URL>"
         }
       }

  3. The run_id returned by AgentOS is stored in rfq.agent_run_id.

  4. GET /api/v1/tracking/rfqs/{id} serializes agent_run_id in the response.

Run without DB (auto-skipped at DB-dependent assertions):
    pytest tests/test_rfq_agentOS_trigger.py -v

Run with DB:
    DATABASE_URL=postgresql+asyncpg://... pytest tests/test_rfq_agentOS_trigger.py -v
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import requires_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FAKE_AGENTOSS_RUN_ID = "run-agentOS-e2e-abc123"
FAKE_AGENTOSS_TASK_ID = "task-agentOS-e2e-xyz"

_AGENTOSS_TASK_RESPONSE = {
    "task": {
        "id": FAKE_AGENTOSS_TASK_ID,
        "status": "pending",
        "plan_id": "plan-001",
    },
    "run": {
        "id": FAKE_AGENTOSS_RUN_ID,
        "status": "running",
    },
}

_RFQ_FORM_PAYLOAD = {
    "email": "buyer@acme.com",
    "full_name": "Alice Buyer",
    "company_name": "ACME Corp",
    "product_interests": ["product-test-001"],
    "timeline": "1-3 months",
    "how_did_you_find_us": "google",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_agentOS_post(received: dict):
    """Return an AsyncMock that captures the AgentOS POST /tasks call."""

    async def _post(url, *, json=None, **kwargs):
        received["url"] = str(url)
        received["payload"] = json
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = _AGENTOSS_TASK_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    return AsyncMock(side_effect=_post)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.asyncio
async def test_rfq_creation_calls_agentOS_with_correct_payload(http_client):
    """
    When a visitor submits an RFQ, ForgeBase must call AgentOS POST /tasks
    with the rfq_id embedded in workflow_input.

    Will fail until:
    - RFQ creation handler includes the AgentOS trigger call.
    """
    received: dict = {}

    with patch("httpx.AsyncClient.post", new=_make_fake_agentOS_post(received)):
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert rfq_response.status_code in (200, 201), rfq_response.text

    assert received, (
        "ForgeBase did NOT call AgentOS after creating the RFQ. "
        "Add the auto-trigger in the RFQ creation handler."
    )

    assert "/tasks" in received["url"], (
        f"AgentOS call went to unexpected URL: {received['url']!r}. "
        "Expected a POST to <AGENTOSS_URL>/tasks."
    )

    payload = received["payload"]
    assert payload["domain"] == "forgebase_rfq", (
        f"Wrong domain sent to AgentOS: {payload.get('domain')!r}. "
        "Expected 'forgebase_rfq'."
    )

    rfq_identifier = (
        rfq_response.json().get("rfq_number") or rfq_response.json().get("id")
    )
    assert str(rfq_identifier) in str(payload["workflow_input"].get("rfq_id", "")), (
        f"AgentOS workflow_input.rfq_id does not match the created RFQ. "
        f"Sent rfq_id={payload['workflow_input'].get('rfq_id')!r}, "
        f"expected rfq identifier={rfq_identifier!r}."
    )


@requires_db
@pytest.mark.asyncio
async def test_rfq_creation_stores_agent_run_id_on_rfq_record(http_client):
    """
    After calling AgentOS, ForgeBase must persist the returned run_id
    into rfq.agent_run_id so the Admin UI can display task status without
    requiring a manual run_id input.

    Will fail until:
    - RFQRequest.agent_run_id field exists.
    - Creation handler persists run_id returned from AgentOS.
    """
    received: dict = {}

    with patch("httpx.AsyncClient.post", new=_make_fake_agentOS_post(received)):
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert rfq_response.status_code in (200, 201), rfq_response.text
    rfq_data = rfq_response.json()

    assert "agent_run_id" in rfq_data, (
        "RFQ creation response does not include agent_run_id. "
        "Add agent_run_id to the RFQRequest model and return it in the response schema."
    )
    assert rfq_data["agent_run_id"] == FAKE_AGENTOSS_RUN_ID, (
        f"agent_run_id mismatch. "
        f"Expected {FAKE_AGENTOSS_RUN_ID!r}, got {rfq_data.get('agent_run_id')!r}. "
        "ForgeBase must store the run_id returned by AgentOS into the RFQ record."
    )


@requires_db
@pytest.mark.asyncio
async def test_rfq_detail_endpoint_exposes_agent_run_id(http_client):
    """
    GET /api/v1/tracking/rfqs/{id} must return agent_run_id so the Admin
    RFQ detail page can display AgentOS task status automatically — without
    requiring the user to manually input a run_id.

    Will fail until:
    - RFQ detail schema includes agent_run_id.
    - agent_run_id is populated from the DB record.
    """
    received: dict = {}

    with patch("httpx.AsyncClient.post", new=_make_fake_agentOS_post(received)):
        create_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert create_response.status_code in (200, 201), create_response.text
    created = create_response.json()
    rfq_id = created.get("id") or created.get("rfq_number")

    get_response = await http_client.get(f"/api/v1/tracking/rfqs/{rfq_id}")
    assert get_response.status_code == 200, get_response.text
    fetched = get_response.json()

    assert "agent_run_id" in fetched, (
        f"GET /tracking/rfqs/{rfq_id} does not return agent_run_id. "
        "Ensure the RFQ detail schema serializes agent_run_id."
    )
    assert fetched["agent_run_id"] == FAKE_AGENTOSS_RUN_ID, (
        f"Fetched agent_run_id={fetched.get('agent_run_id')!r} does not match "
        f"the run_id returned by AgentOS ({FAKE_AGENTOSS_RUN_ID!r}). "
        "Check that the value is persisted and not discarded."
    )
