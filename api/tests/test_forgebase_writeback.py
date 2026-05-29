"""
TDD: ForgeBase RFQ 條件四（Writeback）

=== 條件四：Writeback (test_forgebase_writeback) ===

驗收標準（AGENT.md §5 條件四）：
- 核准後查詢產品 API，確認結果欄位已更新
  （agent_analysis_summary, agent_draft_body 必須非空）
- 結果必須同時存在 AgentOS Evidence 和產品 DB
- 必須驗證寫回動作是冪等的（重複執行不產生重複資料）

實作說明：
- writeback_agentOS_result() 呼叫 AgentOS GET /runs/{run_id}/evidence
- 從 evidence 提取：
    forgebase_analyze_rfq → output.analysis.summary → RFQ.agent_analysis_summary
    forgebase_send_reply  → output.approved_draft.body → RFQ.agent_draft_body
- 測試用 httpx.AsyncClient.get mock 模擬 AgentOS evidence endpoint
- 透過 POST /api/v1/forms/rfq 建立測試 RFQ（與 auto-trigger 相同模式）
- writeback_agentOS_result 的 get_session_ctx 以 _service_test_session_ctx 取代，
  確保在測試 event loop 中使用測試 DB 連線

Run:
    pytest tests/test_forgebase_writeback.py -v
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient

from app.services.agentOS import writeback_agentOS_result
from app.models.rfq_request import RFQRequest
from tests.conftest import _make_engine


# ── 常數：測試用 RFQ 表單 payload ─────────────────────────────────────────────
_RFQ_FORM_PAYLOAD = {
    "full_name": "Writeback Test Buyer",
    "email": "wb@test.de",
    "company_name": "WritebackTest GmbH",
    "phone": "+49-555-0199",
    "country": "DE",
    "job_title": "Procurement Manager",
    "product_ids": [],
    "timeline": "1-3 months",
    "how_did_you_find_us": "google",
    "consent": True,
}

# ── 常數：測試 evidence 資料 ──────────────────────────────────────────────────
_RUN_ID = "run-wb-test-001"
_ANALYSIS_SUMMARY = "Buyer in Germany needs 500 units, urgency high"
_DRAFT_BODY = "Dear Buyer, we are pleased to offer the following proposal..."

_MOCK_EVIDENCE = [
    {
        "id": "ev-001",
        "task_id": "task-wb-test",
        "run_id": _RUN_ID,
        "step_id": "step-analyze",
        "source_type": "tool",
        "source_uri": "forgebase_analyze_rfq",
        "digest": "analyze-rfq:step-analyze",
        "payload": {
            "output": {
                "analysis": {
                    "summary": _ANALYSIS_SUMMARY,
                    "urgency": "high",
                    "quantity": 500,
                }
            },
            "side_effects": [],
            "external_ref": None,
        },
    },
    {
        "id": "ev-002",
        "task_id": "task-wb-test",
        "run_id": _RUN_ID,
        "step_id": "step-send",
        "source_type": "tool",
        "source_uri": "forgebase_send_reply",
        "digest": "send-reply:step-send",
        "payload": {
            "output": {
                "delivery_status": "queued",
                "rfq_id": "rfq-wb-test-001",
                "source": "agentos",
                "approved_draft": {
                    "body": _DRAFT_BODY,
                    "subject": "Re: RFQ #rfq-wb-test-001",
                },
            },
            "side_effects": ["reply_dispatch_queued"],
            "external_ref": None,
        },
    },
]


@asynccontextmanager
async def _service_test_session_ctx():
    """Use test DB sessions inside writeback service to avoid cross-loop pool issues."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            yield db
    finally:
        await eng.dispose()


async def _mock_agentOS_post_noop(self, url, *args, **kwargs):
    """Suppress AgentOS trigger during writeback tests (we only care about GET evidence)."""
    return httpx.Response(
        200,
        json={"run": {"id": "run-auto-trigger-suppressed"}, "task": {"id": "task-suppress"}},
        request=httpx.Request("POST", url),
    )


def _make_selective_post(agentOS_url: str):
    """Return a selective POST mock that only intercepts AgentOS calls."""
    original_post = httpx.AsyncClient.post

    async def selective_post(self, url, *args, **kwargs):
        url_str = str(url)
        if agentOS_url in url_str or "agentoss" in url_str.lower() or ":8000" in url_str:
            return httpx.Response(
                200,
                json={"run": {"id": "run-wb-suppressed"}, "task": {"id": "task-wb-suppressed"}},
                request=httpx.Request("POST", url_str),
            )
        return await original_post(self, url, *args, **kwargs)

    return selective_post


@pytest.mark.asyncio(loop_scope="function")
async def test_forgebase_writeback(http_client: AsyncClient):
    """
    條件四：Writeback 驗收測試

    流程：
    1. 透過 POST /api/v1/forms/rfq 建立 ForgeBase RFQ 記錄
    2. 確認 agent_analysis_summary + agent_draft_body 初始為空
    3. mock AgentOS GET /runs/{run_id}/evidence，呼叫 writeback_agentOS_result
    4. 從 DB 讀取 RFQ，確認 agent_analysis_summary 和 agent_draft_body 已更新
    5. 呼叫第二次（冪等性驗證）— 欄位值不變
    """
    # ── Step 1: 建立 RFQ 記錄（suppress AgentOS auto-trigger）────────────────
    from app.core.config import settings
    selective_post = _make_selective_post(settings.AGENTOSS_URL or "")
    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "post", new=selective_post):
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert rfq_response.status_code in (200, 201), (
        f"RFQ submission failed: {rfq_response.status_code} {rfq_response.text}"
    )
    rfq_id = uuid.UUID(rfq_response.json()["rfq_id"])

    # ── Step 2: 確認寫回欄位初始為空 ─────────────────────────────────────────
    eng, factory = _make_engine()
    async with factory() as db:
        rfq_before = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq_before is not None, f"RFQ {rfq_id} not found in DB"
    assert rfq_before.agent_analysis_summary is None, (
        "agent_analysis_summary 應在 writeback 前為空"
    )
    assert rfq_before.agent_draft_body is None, (
        "agent_draft_body 應在 writeback 前為空"
    )

    # ── Step 3: mock AgentOS evidence endpoint，執行 writeback ───────────────
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            200,
            json=_MOCK_EVIDENCE,
            request=httpx.Request("GET", url),
        )

    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "get", new=mock_get):
        result = await writeback_agentOS_result(rfq_id, _RUN_ID)

    assert result is True, "writeback_agentOS_result 應回傳 True 表示成功"

    # ── Step 4: 確認 DB 已更新 ───────────────────────────────────────────────
    eng, factory = _make_engine()
    async with factory() as db:
        rfq_after = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq_after.agent_analysis_summary == _ANALYSIS_SUMMARY, (
        f"agent_analysis_summary 應為 {_ANALYSIS_SUMMARY!r}，"
        f"實際為 {rfq_after.agent_analysis_summary!r}"
    )
    assert rfq_after.agent_draft_body == _DRAFT_BODY, (
        f"agent_draft_body 應為 {_DRAFT_BODY!r}，"
        f"實際為 {rfq_after.agent_draft_body!r}"
    )

    # ── Step 5: 冪等性驗證 ───────────────────────────────────────────────────
    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "get", new=mock_get):
        result2 = await writeback_agentOS_result(rfq_id, _RUN_ID)

    assert result2 is True, "第二次 writeback 應仍回傳 True"

    eng, factory = _make_engine()
    async with factory() as db:
        rfq_idempotent = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq_idempotent.agent_analysis_summary == _ANALYSIS_SUMMARY, (
        "冪等性違反：agent_analysis_summary 在第二次 writeback 後發生變化"
    )
    assert rfq_idempotent.agent_draft_body == _DRAFT_BODY, (
        "冪等性違反：agent_draft_body 在第二次 writeback 後發生變化"
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_forgebase_writeback_partial_evidence(http_client: AsyncClient):
    """
    條件四附加：僅有部分 evidence 時的寫回行為

    若 AgentOS 只有 analyze-rfq evidence（send-reply 尚未執行），
    writeback 應只更新 agent_analysis_summary，不覆蓋 agent_draft_body（維持 None）。
    """
    from app.core.config import settings
    selective_post = _make_selective_post(settings.AGENTOSS_URL or "")
    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "post", new=selective_post):
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json={**_RFQ_FORM_PAYLOAD, "email": "partial@test.de", "company_name": "PartialWB Corp"},
        )

    assert rfq_response.status_code in (200, 201), (
        f"RFQ submission failed: {rfq_response.status_code} {rfq_response.text}"
    )
    rfq_id = uuid.UUID(rfq_response.json()["rfq_id"])

    # 只提供 analyze-rfq evidence
    partial_evidence = [_MOCK_EVIDENCE[0]]

    async def mock_get_partial(self, url, **kwargs):
        return httpx.Response(
            200,
            json=partial_evidence,
            request=httpx.Request("GET", url),
        )

    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "get", new=mock_get_partial):
        result = await writeback_agentOS_result(rfq_id, _RUN_ID)

    assert result is True

    eng, factory = _make_engine()
    async with factory() as db:
        rfq = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq.agent_analysis_summary == _ANALYSIS_SUMMARY, (
        "agent_analysis_summary 應被 analyze-rfq evidence 更新"
    )
    assert rfq.agent_draft_body is None, (
        "agent_draft_body 應維持 None，因為 send-reply evidence 尚未存在"
    )

