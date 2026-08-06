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

import uuid
from contextlib import asynccontextmanager

import httpx
import pytest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.models.rfq_request import RFQRequest
from tests.conftest import requires_db, _make_engine

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
    "country": "US",
    "product_interests": ["product-test-001"],
    "timeline": "1-3 months",
    "how_did_you_find_us": "google",
    "consent": True,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _service_test_session_ctx():
    """Isolated NullPool session for app.services.agentOS to avoid cross-loop issues."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            yield db
    finally:
        await eng.dispose()


def _make_fake_agentOS_post(received: dict):
    """Selective httpx mock: intercept only AgentOS POST /tasks, pass everything else through.

    注意：patch 的目標是 httpx.AsyncClient.post，測試自己的 http_client 也走同一個
    方法；若不選擇性攔截，第一個被捕捉的會是測試送出的 /api/v1/forms/rfq 請求本身，
    導致請求根本到不了 app（這正是先前三個測試失敗的根因）。
    """
    original_post = httpx.AsyncClient.post
    agentOS_task_url = f"{settings.AGENTOSS_URL}/tasks"

    async def _post(self, url, *args, **kwargs):
        url_str = str(url)
        if url_str == agentOS_task_url:
            received["url"] = url_str
            received["payload"] = kwargs.get("json")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = _AGENTOSS_TASK_RESPONSE
            mock_resp.raise_for_status = MagicMock()
            return mock_resp
        return await original_post(self, url, *args, **kwargs)

    return _post


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

    with (
        patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx),
        patch.object(httpx.AsyncClient, "post", new=_make_fake_agentOS_post(received)),
    ):
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

    # workflow_input.rfq_id 綁定的是 RFQRequest.id（UUID），不是 rfq_number
    rfq_identifier = rfq_response.json()["rfq_id"]
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

    驗證方式說明：公開表單回應刻意不含 agent_run_id（內部 run id 不應暴露給
    訪客），因此直接查 DB 驗證持久化；Admin 端的序列化由
    test_rfq_detail_endpoint_exposes_agent_run_id 覆蓋。
    """
    received: dict = {}

    with (
        patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx),
        patch.object(httpx.AsyncClient, "post", new=_make_fake_agentOS_post(received)),
    ):
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert rfq_response.status_code in (200, 201), rfq_response.text
    rfq_id = uuid.UUID(rfq_response.json()["rfq_id"])

    eng, factory = _make_engine()
    async with factory() as db:
        rfq = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq is not None, f"RFQ {rfq_id} 在資料庫中找不到"
    assert rfq.agent_run_id == FAKE_AGENTOSS_RUN_ID, (
        f"agent_run_id mismatch. "
        f"Expected {FAKE_AGENTOSS_RUN_ID!r}, got {rfq.agent_run_id!r}. "
        "ForgeBase must store the run_id returned by AgentOS into the RFQ record."
    )


@requires_db
@pytest.mark.asyncio
async def test_rfq_detail_endpoint_exposes_agent_run_id(http_client):
    """
    GET /api/v1/tracking/rfqs/{id} must return agent_run_id so the Admin
    RFQ detail page can display AgentOS task status automatically — without
    requiring the user to manually input a run_id.

    此端點需要登入（get_current_user）；測試建立 tenantless admin
    （tenant_id=None 可跨租戶讀取，與 production seed admin 相同）。
    """
    from app.core.security import create_access_token, get_password_hash
    from app.models.user import User

    received: dict = {}

    with (
        patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx),
        patch.object(httpx.AsyncClient, "post", new=_make_fake_agentOS_post(received)),
    ):
        create_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert create_response.status_code in (200, 201), create_response.text
    rfq_id = create_response.json()["rfq_id"]

    eng, factory = _make_engine()
    async with factory() as session:
        admin = User(
            email=f"agentos-admin-{uuid.uuid4().hex[:8]}@test.invalid",
            hashed_password=get_password_hash("testpass"),
            full_name="AgentOS Test Admin",
            role="admin",
            tenant_id=None,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        admin_id = admin.id
        token = create_access_token(str(admin_id))

    try:
        get_response = await http_client.get(
            f"/api/v1/tracking/rfqs/{rfq_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
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
    finally:
        async with factory() as session:
            row = await session.get(User, admin_id)
            if row:
                await session.delete(row)
                await session.commit()
        await eng.dispose()
