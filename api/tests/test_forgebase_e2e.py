"""
TDD: ForgeBase RFQ 條件五（E2E）完整流程驗收

完整流程（全程不依賴手動操作，全部 mock 外部 HTTP）：

1. ForgeBase 提交 RFQ → 自動觸發 AgentOS POST /tasks
2. AgentOS 內部 WorkflowService 執行：
     analyze-rfq  (READONLY, 自動通過)
     draft-reply  (READONLY, 自動通過)
     review-draft (REVERSIBLE_WRITE, Gate 1 暫停)
3. 驗 ForgeBase rfq.agent_run_id 已綁定
4. 第一次核准 (Gate 1) → run 繼續執行
5. send-reply  (IRREVERSIBLE_WRITE, Gate 2 暫停)
6. 第二次核准 (Gate 2) → run 完成
7. mock GET /runs/{run_id}/evidence 回傳真實 evidence
8. writeback_agentOS_result 寫回 ForgeBase RFQ
9. 驗 agent_analysis_summary + agent_draft_body 已填入 RFQ 紀錄

Run:
    pytest tests/test_forgebase_e2e.py -v
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.models.rfq_request import RFQRequest
from app.services.agentOS import writeback_agentOS_result
from tests.conftest import _make_engine

pytestmark: list = []

# ── 測試常數 ─────────────────────────────────────────────────────────────────

_E2E_ANALYSIS_SUMMARY = "E2E Buyer needs 300 units of steel frame, delivery within 30 days"
_E2E_DRAFT_BODY = "Dear E2E Buyer, we are pleased to confirm availability of 300 units."

_RFQ_FORM_PAYLOAD = {
    "full_name": "E2E Integration Buyer",
    "email": "e2e@test.de",
    "company_name": "E2E Integration GmbH",
    "phone": "+49-555-0301",
    "country": "DE",
    "job_title": "Procurement Director",
    "product_ids": [],
    "timeline": "immediate",
    "how_did_you_find_us": "referral",
    "consent": True,
}


@asynccontextmanager
async def _service_test_session_ctx():
    """ForgeBase DB session for writeback service (NullPool, test-safe)."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            yield db
    finally:
        await eng.dispose()


# ── E2E 測試 ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
async def test_forgebase_e2e(http_client: AsyncClient):
    """
    條件五 E2E：完整 ForgeBase ↔ AgentOS 整合流程

    驗收標準（AGENT.md §5 條件五）：
    - 完整流程：業務事件觸發 → Task 建立 → 執行到 Gate 1 → 核准
              → 執行到 Gate 2 → 核准 → 回寫
    - 不依賴任何手動操作
    - 不依賴真實外部 API（全部 mock）
    - 可在 CI 環境直接跑通

    技術注意：
    - AgentOS service.run_task() / decide_approval() 內部呼叫 asyncio.run()
      在已有 event loop 的 async 測試中必須透過 asyncio.to_thread() 執行，
      讓 service 在 thread pool 裡建立獨立的 event loop，避免衝突。
    """
    pytest.importorskip(
        "agent_platform",
        reason="AgentOS runtime package（外部獨立產品）未安裝於此環境；此測試僅在 AgentOS repo 環境執行",
    )
    from sqlalchemy import create_engine
    from sqlalchemy.pool import StaticPool
    from agent_platform.persistence.tables import (
        TaskTable, PlanTable, StepTable, SessionTable,
        RunTable, RunStateTable, CheckpointTable, EvidenceTable,
        ApprovalTable, ToolCallTable,
    )
    from agent_platform.persistence import SqlRepository
    from agent_platform.bootstrap import (
        build_default_adapter_registry,
        build_default_workflow_registry,
        default_execution_policies,
    )
    from agent_platform.service import WorkflowService
    from agent_platform.models import (
        ApprovalDecision as AD,
        ApprovalDecisionRequest,
        TaskCreateRequest,
        RunStatus,
    )
    from agent_platform.contracts import ProductCapabilities, StepExecutionResult

    # ── 建立 AgentOS 內部服務（獨立 SQLite，不影響 ForgeBase DB）─────────────
    agentos_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tbl_cls in [
        TaskTable, PlanTable, StepTable, SessionTable,
        RunTable, RunStateTable, CheckpointTable, EvidenceTable,
        ApprovalTable, ToolCallTable,
    ]:
        tbl_cls.__table__.create(agentos_engine, checkfirst=True)

    class _FakeForgeBaseAdapter:
        """
        Fake ForgeBase adapter for E2E.

        output format matches what writeback_agentOS_result expects:
          analyze-rfq  → output.analysis.summary
          send-reply   → output.approved_draft.body
        """

        @property
        def product_key(self) -> str:
            return "forgebase"

        def capabilities(self) -> ProductCapabilities:
            return ProductCapabilities()

        async def execute_step(self, request) -> StepExecutionResult:
            step_name = request.step_name
            evidence_chain = request.context.get("evidence_chain", [])

            if step_name == "analyze-rfq":
                return StepExecutionResult(
                    output={
                        "analysis": {
                            "summary": _E2E_ANALYSIS_SUMMARY,
                            "urgency": "high",
                            "quantity": 300,
                        }
                    },
                    external_ref="a-e2e-001",
                )

            if step_name == "draft-reply":
                return StepExecutionResult(
                    output={
                        "body": _E2E_DRAFT_BODY,
                        "subject": "Re: Your RFQ — 300 units available",
                        "analysis_summary": _E2E_ANALYSIS_SUMMARY,
                    },
                    external_ref="d-e2e-001",
                )

            if step_name == "review-draft":
                # Pull draft from evidence chain (forgebase_draft_reply)
                draft_out = next(
                    (ev["payload"]["output"] for ev in evidence_chain
                     if ev["source_uri"] == "forgebase_draft_reply"),
                    {"body": _E2E_DRAFT_BODY, "subject": "Re: Your RFQ"},
                )
                return StepExecutionResult(
                    output={
                        "review_packet": {
                            "draft": {
                                "body": draft_out["body"],
                                "subject": draft_out.get("subject", "Re: Your RFQ"),
                                "analysis_summary": _E2E_ANALYSIS_SUMMARY,
                            }
                        }
                    }
                )

            if step_name == "send-reply":
                # Pull review_packet from evidence chain (forgebase_prepare_send)
                review_out = next(
                    (ev["payload"]["output"] for ev in evidence_chain
                     if ev["source_uri"] == "forgebase_prepare_send"),
                    {},
                )
                approved_draft = review_out.get("review_packet", {}).get(
                    "draft", {"body": _E2E_DRAFT_BODY, "subject": "Re: Your RFQ"}
                )
                return StepExecutionResult(
                    output={
                        "delivery_status": "queued",
                        "approved_draft": {
                            "body": approved_draft["body"],
                            "subject": approved_draft.get("subject", "Re: Your RFQ"),
                        },
                    },
                    side_effects=["reply_dispatch_queued"],
                )

            raise AssertionError(f"E2E adapter: unexpected step {step_name!r}")

    fake_adapter = _FakeForgeBaseAdapter()
    adapter_registry = build_default_adapter_registry()
    adapter_registry.replace(fake_adapter)

    service = WorkflowService(
        repository=SqlRepository(agentos_engine),
        adapter_registry=adapter_registry,
        workflow_registry=build_default_workflow_registry(),
        base_execution_policies=default_execution_policies(),
    )

    # Shared state: captured inside mock POST, read by the test
    _agentos_state: dict = {}
    agentOS_task_url = f"{settings.AGENTOSS_URL}/tasks"
    original_post = httpx.AsyncClient.post

    async def mock_agentOS_post(self, url, *args, **kwargs):
        """
        Intercepts ForgeBase → AgentOS POST /tasks.

        1. Creates the task in the internal WorkflowService (sync, safe)
        2. Runs the task in a thread (avoids nested asyncio.run() error)
        3. Returns the real task/run IDs to ForgeBase so agent_run_id is accurate
        """
        url_str = str(url)
        if url_str == agentOS_task_url:
            json_body = kwargs.get("json", {})
            # create_task is sync (pure DB writes, no asyncio.run)
            task_view = service.create_task(TaskCreateRequest(**json_body))
            # run_task calls asyncio.run() internally; thread avoids nested-loop error
            run_view = await asyncio.to_thread(service.run_task, task_view.task.id)
            _agentos_state["task_id"] = task_view.task.id
            _agentos_state["run_id"] = run_view.run.id
            _agentos_state["run_view"] = run_view
            return httpx.Response(
                200,
                json={
                    "task": {"id": task_view.task.id, "status": "running"},
                    "run": {"id": run_view.run.id, "status": run_view.run.status.value},
                },
                request=httpx.Request("POST", url_str),
            )
        # All other POST calls (ForgeBase internal) pass through normally
        return await original_post(self, url, *args, **kwargs)

    # ── Step 1: ForgeBase 提交 RFQ，AgentOS 自動觸發並執行到 Gate 1 ──────────
    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "post", new=mock_agentOS_post):
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )

    assert rfq_response.status_code in (200, 201), (
        f"ForgeBase RFQ 建立失敗：{rfq_response.status_code} {rfq_response.text}"
    )
    rfq_id = uuid.UUID(rfq_response.json()["rfq_id"])

    run_id = _agentos_state.get("run_id")
    assert run_id, (
        "AgentOS mock POST 未被呼叫，或 _agentos_state 未填入 run_id。"
        "請確認 AGENTOSS_URL 設定與 trigger_agentOS_rfq 函式正確執行。"
    )

    # ── 驗 2a：ForgeBase rfq.agent_run_id 已綁定到 AgentOS run ───────────────
    eng, factory = _make_engine()
    async with factory() as db:
        rfq_after_trigger = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq_after_trigger is not None, f"ForgeBase DB 找不到 RFQ {rfq_id}"
    assert rfq_after_trigger.agent_run_id == run_id, (
        f"ForgeBase 綁定失敗：rfq.agent_run_id={rfq_after_trigger.agent_run_id!r}，"
        f"應為 AgentOS run_id={run_id!r}"
    )

    # ── 驗 2b：AgentOS 停在 Gate 1（review-draft, WAITING_APPROVAL）──────────
    run_view_gate1 = _agentos_state["run_view"]
    assert run_view_gate1.run.status == RunStatus.WAITING_APPROVAL, (
        f"AgentOS 應停在 Gate 1 (review-draft)，"
        f"實際 status={run_view_gate1.run.status!r}"
    )
    assert "review-draft" in run_view_gate1.run_state.summary, (
        f"Gate 1 run_state.summary={run_view_gate1.run_state.summary!r}，應含 'review-draft'"
    )

    pending_gate1 = [a for a in run_view_gate1.approvals if a.decision == AD.PENDING]
    assert len(pending_gate1) == 1, (
        f"Gate 1 應有 1 個 PENDING approval，得到 {len(pending_gate1)}"
    )
    gate1_approval_id = pending_gate1[0].id

    # ── Step 3: 第一次核准 Gate 1（review-draft REVERSIBLE_WRITE）────────────
    # decide_approval also calls asyncio.run(); run in thread
    run_view_after_gate1 = await asyncio.to_thread(
        service.decide_approval,
        gate1_approval_id,
        ApprovalDecisionRequest(decision=AD.APPROVED, actor_id="sales-manager-e2e"),
    )

    # ── 驗 4：Gate 1 核准後停在 Gate 2（send-reply, WAITING_APPROVAL）─────────
    assert run_view_after_gate1.run.status == RunStatus.WAITING_APPROVAL, (
        f"Gate 1 核准後應停在 Gate 2 (send-reply)，"
        f"實際 status={run_view_after_gate1.run.status!r}"
    )
    assert "send-reply" in run_view_after_gate1.run_state.summary, (
        f"Gate 2 run_state.summary={run_view_after_gate1.run_state.summary!r}，應含 'send-reply'"
    )

    # RunView.approvals 含本次 run 全部 approval（含已核准的 Gate 1）
    # 必須過濾 PENDING 才是 Gate 2
    pending_gate2 = [a for a in run_view_after_gate1.approvals if a.decision == AD.PENDING]
    assert len(pending_gate2) == 1, (
        f"Gate 2 應有 1 個 PENDING approval，得到 {len(pending_gate2)}"
    )
    gate2_approval_id = pending_gate2[0].id

    # ── Step 5: 第二次核准 Gate 2（send-reply IRREVERSIBLE_WRITE）────────────
    run_view_final = await asyncio.to_thread(
        service.decide_approval,
        gate2_approval_id,
        ApprovalDecisionRequest(decision=AD.APPROVED, actor_id="sales-director-e2e"),
    )

    # ── 驗 6：兩次核准後 run 達 completed ────────────────────────────────────
    assert run_view_final.run.status == RunStatus.COMPLETED, (
        f"兩次核准後 run 應為 completed，"
        f"實際={run_view_final.run.status!r}"
    )

    # ── Step 7：從 AgentOS 取出真實 evidence，確認格式完整 ────────────────────
    evidence_objects = service.repository.list_evidence(run_id)
    evidence_by_source = {ev.source_uri: ev.payload for ev in evidence_objects}

    assert "forgebase_analyze_rfq" in evidence_by_source, (
        "analyze-rfq evidence 缺失；writeback 無法取得 agent_analysis_summary"
    )
    assert "forgebase_send_reply" in evidence_by_source, (
        "send-reply evidence 缺失；writeback 無法取得 agent_draft_body"
    )

    # 序列化成 HTTP response JSON 格式（與 GET /runs/{run_id}/evidence 一致）
    evidence_json = [
        {
            "id": ev.id,
            "task_id": ev.task_id,
            "run_id": ev.run_id,
            "step_id": ev.step_id,
            "source_type": ev.source_type,
            "source_uri": ev.source_uri,
            "digest": ev.digest,
            "payload": ev.payload,
        }
        for ev in evidence_objects
    ]

    async def mock_agentOS_get(self, url, **kwargs):
        """Mock GET /runs/{run_id}/evidence，回傳內部 service 的真實 evidence。"""
        url_str = str(url)
        if f"/runs/{run_id}/evidence" in url_str:
            return httpx.Response(
                200,
                json=evidence_json,
                request=httpx.Request("GET", url_str),
            )
        raise AssertionError(f"E2E test: 未預期的 GET 請求 {url_str!r}")

    # ── Step 8: writeback_agentOS_result 寫回 ForgeBase RFQ ──────────────────
    with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
         patch.object(httpx.AsyncClient, "get", new=mock_agentOS_get):
        writeback_result = await writeback_agentOS_result(rfq_id, run_id)

    assert writeback_result is True, (
        "writeback_agentOS_result 應回傳 True 表示成功寫回"
    )

    # ── 最終驗收：ForgeBase RFQ 所有欄位完整 ─────────────────────────────────
    eng, factory = _make_engine()
    async with factory() as db:
        rfq_final = await db.get(RFQRequest, rfq_id)
    await eng.dispose()

    assert rfq_final.agent_run_id == run_id, (
        f"最終 agent_run_id={rfq_final.agent_run_id!r}，應為 {run_id!r}"
    )
    assert rfq_final.agent_analysis_summary == _E2E_ANALYSIS_SUMMARY, (
        f"agent_analysis_summary={rfq_final.agent_analysis_summary!r}，"
        f"應為 {_E2E_ANALYSIS_SUMMARY!r}"
    )
    assert rfq_final.agent_draft_body == _E2E_DRAFT_BODY, (
        f"agent_draft_body={rfq_final.agent_draft_body!r}，"
        f"應為 {_E2E_DRAFT_BODY!r}"
    )
