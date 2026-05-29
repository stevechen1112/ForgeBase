"""
TDD: ForgeBase RFQ auto-trigger 條件一 — 正向 & 負向驗證

Acceptance Criteria (Condition 1 - Auto-trigger):

正向驗證 (test_forgebase_auto_trigger):
- RFQ 建立時，ForgeBase 自動呼叫 AgentOS POST /tasks
- AgentOS 返回 run_id
- run_id 自動儲存到 RFQ.agent_run_id
- 查詢 ForgeBase GET /tracking/rfqs/{id} 返回 agent_run_id

負向驗證 (test_forgebase_auto_trigger_agentOS_unavailable):
- AgentOS 無回應/連線錯誤/超時
- RFQ 仍然建立成功（核心業務不中斷）
- RFQ.agent_run_id 為 null
- 錯誤被記錄到 RFQEvent 或日誌中

Run:
    pytest tests/test_forgebase_auto_trigger.py -v
"""

import json
import uuid
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch
import httpx

import pytest
from httpx import AsyncClient, ConnectError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.rfq_request import RFQRequest
from tests.conftest import _make_engine

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# Constants & Test Data
# ─────────────────────────────────────────────────────────────────────────────

FAKE_AGENTOSS_TASK_ID = "task-forgebase-rfq-abc123"
FAKE_AGENTOSS_RUN_ID = "run-forgebase-rfq-xyz789"

_AGENTOSS_SUCCESS_RESPONSE = {
    "task": {
        "id": FAKE_AGENTOSS_TASK_ID,
        "status": "pending",
    },
    "run": {
        "id": FAKE_AGENTOSS_RUN_ID,
        "status": "running",
    },
}

_RFQ_FORM_PAYLOAD = {
    "full_name": "Test Buyer",
    "email": "buyer@test.com",
    "company_name": "Test Corp",
    "phone": "+1-555-0100",
    "country": "US",
    "job_title": "Procurement Manager",
    "product_ids": [],  # Empty to avoid FK constraint violations in test
    "timeline": "1-3 months",
    "how_did_you_find_us": "google",
    "consent": True,
}


@asynccontextmanager
async def _service_test_session_ctx():
    """Use test DB sessions inside app.services.agentOS to avoid cross-loop pool issues in tests."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            yield db
    finally:
        await eng.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

async def test_forgebase_auto_trigger(http_client: AsyncClient):
    """
    正向驗證：RFQ 建立 → AgentOS 自動觸發 → run_id 存入 RFQ
    """
    agentOS_task_url = f"{settings.AGENTOSS_URL}/tasks"
    original_post = httpx.AsyncClient.post
    agentOS_calls = []

    async def selective_post(self, url, *args, **kwargs):
        url_str = str(url)
        if url_str == agentOS_task_url:
            agentOS_calls.append({
                "url": url_str,
                "json": kwargs.get("json"),
            })
            return httpx.Response(
                status_code=200,
                json=_AGENTOSS_SUCCESS_RESPONSE,
                request=httpx.Request("POST", url_str),
            )
        return await original_post(self, url, *args, **kwargs)

    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "post", new=selective_post):
        # 1. 提交 RFQ 表單
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

        assert rfq_response.status_code in (200, 201), (
            f"RFQ submission failed: {rfq_response.status_code} {rfq_response.text}"
        )
        rfq_data = rfq_response.json()
        rfq_id = rfq_data.get("rfq_id")

        assert rfq_id, "RFQ creation response missing rfq_id"
        rfq_id_uuid = uuid.UUID(rfq_id)

    # 2. 從資料庫查詢 RFQ
    eng, factory = _make_engine()
    async with factory() as db:
        rfq = await db.get(RFQRequest, rfq_id_uuid)
        assert rfq, f"RFQ {rfq_id} not found in database"
    await eng.dispose()

    # 3. 檢查 agent_run_id 被成功設定
    assert hasattr(rfq, "agent_run_id"), (
        "RFQRequest model missing 'agent_run_id' attribute"
    )
    assert rfq.agent_run_id == FAKE_AGENTOSS_RUN_ID, (
        f"agent_run_id mismatch. Expected {FAKE_AGENTOSS_RUN_ID!r}, got {rfq.agent_run_id!r}"
    )

    # 4. 驗證建立端點有經過 trigger_agentOS_rfq（以 AgentOS URL 呼叫為證）
    assert len(agentOS_calls) == 1, (
        "Expected exactly one AgentOS /tasks call during RFQ creation, "
        f"got {len(agentOS_calls)}"
    )
    assert agentOS_calls[0]["url"] == agentOS_task_url
    assert agentOS_calls[0]["json"].get("workflow_input", {}).get("source_id") == str(rfq_id_uuid)


async def test_forgebase_auto_trigger_agentOS_unavailable(http_client: AsyncClient):
    """
    負向驗證：AgentOS 無回應 → RFQ 仍建立成功 → agent_run_id 為 null
    """
    agentOS_task_url = f"{settings.AGENTOSS_URL}/tasks"
    original_post = httpx.AsyncClient.post
    agentOS_calls = []

    async def selective_post_fail(self, url, *args, **kwargs):
        url_str = str(url)
        if url_str == agentOS_task_url:
            agentOS_calls.append(url_str)
            raise ConnectError(
                "AgentOS unreachable",
                request=httpx.Request("POST", url_str),
            )
        return await original_post(self, url, *args, **kwargs)

    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "post", new=selective_post_fail):
        # 1. 提交 RFQ 表單（儘管 trigger 會失敗）
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

        # RFQ 建立應該成功，即使 trigger 失敗
        assert rfq_response.status_code in (200, 201), (
            f"RFQ submission should succeed when trigger fails. "
            f"Got: {rfq_response.status_code}"
        )
        rfq_data = rfq_response.json()
        rfq_id = rfq_data.get("rfq_id")
        assert rfq_id, "RFQ creation response missing rfq_id"
        rfq_id_uuid = uuid.UUID(rfq_id)

    # 2. 從資料庫查詢 RFQ
    eng, factory = _make_engine()
    async with factory() as db:
        rfq = await db.get(RFQRequest, rfq_id_uuid)
        assert rfq, f"RFQ {rfq_id} not found in database"
    await eng.dispose()

    # 3. agent_run_id 應為 null（因 trigger 失敗）
    assert hasattr(rfq, "agent_run_id"), "RFQRequest missing agent_run_id"
    assert rfq.agent_run_id is None, (
        f"When trigger fails, agent_run_id should be null, got {rfq.agent_run_id!r}"
    )

    # 4. 驗證端點確實有嘗試呼叫 AgentOS
    assert len(agentOS_calls) == 1, (
        "Expected one AgentOS /tasks call even when unavailable, "
        f"got {len(agentOS_calls)}"
    )
