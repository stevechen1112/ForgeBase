"""
TDD: ForgeBase RFQ 條件二（Binding）+ 條件三（Approval Gate）

=== 條件二：雙向綁定 (test_forgebase_binding) ===

驗收標準（AGENT.md §5 條件二）：
- 查詢產品 API 確認業務紀錄的 agent_run_id 存在
- 查詢 AgentOS API 確認 task 的 source_id 對應到這筆業務紀錄
- 兩端都確認才算通過

實作注意：
- AgentOS Task 沒有獨立的 source_id 欄位；ForgeBase 透過兩個機制建立可驗證的綁定：
  1. workflow_input.source_id = rfq_id  → AgentOS 執行時可存取
  2. idempotency_key = str(rfq_id)      → 儲存在 Task 模型，可由 GET /tasks/{id} 查詢
- 測試以捕捉送出的 POST /tasks payload 作為「AgentOS 側記錄」來驗證雙向綁定
- 同時以獨立的 httpx GET 呼叫模擬「查詢 AgentOS API」步驟

=== 條件三：Approval Gate (test_forgebase_approval_gate) ===

驗收標準（AGENT.md §5 條件三）：
- ForgeBase workflow 的 READONLY 步驟（analyze-rfq, draft-reply）不被 approval gate 攔截
- 需要 approval 的步驟確實暫停，外部副作用在核准前不發生
- 核准後執行繼續，run 最終完成

實作注意：
- ForgeBase rfq_pipeline 的 gate 在 review-draft 步驟：
  side_effect_level=REVERSIBLE_WRITE + required_permission="prepare_send"（在 approval_required_for 中）
  → _requires_approval 透過 privileged_action=True 回傳 True
- READONLY steps 透過 side_effect_level==READONLY 短路回傳 False（不需 approval）
- 使用 TestClient(create_app("sqlite://")) 直接測試 AgentOS service

Run:
    pytest tests/test_forgebase_binding_approval.py -v
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import httpx
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.models.rfq_request import RFQRequest
from tests.conftest import _make_engine

pytestmark: list = []  # individual tests carry their own marks


# ─────────────────────────────────────────────────────────────────────────────
# Shared constants (re-use from condition 1 test for consistency)
# ─────────────────────────────────────────────────────────────────────────────

FAKE_AGENTOSS_TASK_ID = "task-forgebase-rfq-abc123"
FAKE_AGENTOSS_RUN_ID = "run-forgebase-rfq-xyz789"

_AGENTOSS_SUCCESS_RESPONSE = {
    "task": {"id": FAKE_AGENTOSS_TASK_ID, "status": "pending"},
    "run": {"id": FAKE_AGENTOSS_RUN_ID, "status": "running"},
}

_RFQ_FORM_PAYLOAD = {
    "full_name": "Binding Test Buyer",
    "email": "binding@test.com",
    "company_name": "Binding Corp",
    "phone": "+1-555-0200",
    "country": "US",
    "job_title": "Procurement Manager",
    "product_ids": [],
    "timeline": "1-3 months",
    "how_did_you_find_us": "google",
    "consent": True,
}


@asynccontextmanager
async def _service_test_session_ctx():
    """Isolated NullPool session for app.services.agentOS to avoid cross-loop issues."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            yield db
    finally:
        await eng.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# 條件二：test_forgebase_binding
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio(loop_scope="function")
async def test_forgebase_binding(http_client: AsyncClient):
    """
    條件二：雙向綁定驗證

    ForgeBase 端：rfq.agent_run_id 非空，指向 AgentOS run
    AgentOS 端：POST /tasks payload 的 idempotency_key 和 workflow_input.source_id
                 均為 rfq_id；GET /runs/{run_id} 可查回 task 的 idempotency_key

    兩端都確認才算通過。
    """
    agentOS_task_url = f"{settings.AGENTOSS_URL}/tasks"
    agentOS_run_url_prefix = f"{settings.AGENTOSS_URL}/runs/"
    original_post = httpx.AsyncClient.post
    original_get = httpx.AsyncClient.get

    captured_task_payload: dict = {}

    async def selective_post(self, url, *args, **kwargs):
        url_str = str(url)
        if url_str == agentOS_task_url:
            captured_task_payload.update(kwargs.get("json") or {})
            return httpx.Response(
                status_code=200,
                json=_AGENTOSS_SUCCESS_RESPONSE,
                request=httpx.Request("POST", url_str),
            )
        return await original_post(self, url, *args, **kwargs)

    async def selective_get(self, url, *args, **kwargs):
        url_str = str(url)
        if url_str.startswith(agentOS_run_url_prefix):
            # Simulate AgentOS GET /runs/{run_id} returning task with idempotency_key
            return httpx.Response(
                status_code=200,
                json={
                    "run": {
                        "id": FAKE_AGENTOSS_RUN_ID,
                        "task_id": FAKE_AGENTOSS_TASK_ID,
                        "status": "running",
                    },
                    "run_state": {
                        "run_id": FAKE_AGENTOSS_RUN_ID,
                        "step_outputs": {},
                        "summary": "running",
                    },
                    "approvals": [],
                    "checkpoints": [],
                    "task": {
                        "id": FAKE_AGENTOSS_TASK_ID,
                        # idempotency_key is echoed from what ForgeBase sent
                        "idempotency_key": captured_task_payload.get("idempotency_key"),
                    },
                },
                request=httpx.Request("GET", url_str),
            )
        return await original_get(self, url, *args, **kwargs)

    with (
        patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx),
        patch.object(httpx.AsyncClient, "post", new=selective_post),
        patch.object(httpx.AsyncClient, "get", new=selective_get),
    ):
        # ── 1. ForgeBase 提交 RFQ ──────────────────────────────────────────
        rfq_response = await http_client.post(
            "/api/v1/forms/rfq",
            json=_RFQ_FORM_PAYLOAD,
        )
        assert rfq_response.status_code in (200, 201), (
            f"RFQ 提交失敗: {rfq_response.status_code} {rfq_response.text}"
        )
        rfq_id = rfq_response.json().get("rfq_id")
        assert rfq_id, "RFQ response 缺少 rfq_id"
        rfq_id_uuid = uuid.UUID(rfq_id)

        # ── 2. 查詢 AgentOS API：GET /runs/{run_id}，驗 task.idempotency_key ──
        async with httpx.AsyncClient() as agentos_client:
            run_response = await agentos_client.get(
                f"{settings.AGENTOSS_URL}/runs/{FAKE_AGENTOSS_RUN_ID}"
            )
        assert run_response.status_code == 200
        run_data = run_response.json()

        agentOS_task_idempotency_key = run_data["task"]["idempotency_key"]
        assert agentOS_task_idempotency_key is not None, (
            "AgentOS task.idempotency_key 應為 rfq_id，不可為 None"
        )
        assert agentOS_task_idempotency_key == str(rfq_id_uuid), (
            f"AgentOS 側綁定失敗：task.idempotency_key={agentOS_task_idempotency_key!r}，"
            f"預期 rfq_id={rfq_id_uuid!r}"
        )

    # ── 3. 查詢 ForgeBase DB：驗 agent_run_id 已儲存 ──────────────────────
    eng, factory = _make_engine()
    async with factory() as db:
        rfq = await db.get(RFQRequest, rfq_id_uuid)
        assert rfq, f"RFQ {rfq_id} 在資料庫中找不到"
    await eng.dispose()

    assert rfq.agent_run_id == FAKE_AGENTOSS_RUN_ID, (
        f"ForgeBase 側綁定失敗：rfq.agent_run_id={rfq.agent_run_id!r}，"
        f"預期 {FAKE_AGENTOSS_RUN_ID!r}"
    )

    # ── 4. 驗 POST /tasks payload 包含正確的綁定欄位 ──────────────────────
    assert captured_task_payload.get("idempotency_key") == str(rfq_id_uuid), (
        f"POST /tasks payload 缺少 idempotency_key=rfq_id；"
        f"實際: {captured_task_payload.get('idempotency_key')!r}"
    )
    assert captured_task_payload.get("workflow_input", {}).get("source_id") == str(rfq_id_uuid), (
        f"POST /tasks payload.workflow_input.source_id 應為 rfq_id；"
        f"實際: {captured_task_payload.get('workflow_input', {}).get('source_id')!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 條件三：test_forgebase_approval_gate
# ─────────────────────────────────────────────────────────────────────────────

def test_forgebase_approval_gate():
    """
    條件三：Approval Gate 驗證（兩個獨立 gate）

    ForgeBase RFQ pipeline 有兩個 approval gate：
      Gate 1 — review-draft（REVERSIBLE_WRITE）：
        業務確認草稿內容，可修改，尚未對外發送
      Gate 2 — send-reply（IRREVERSIBLE_WRITE）：
        業務確認真的要發給買家，回覆一旦發出無法收回

    測試流程：
    1. analyze-rfq（READONLY）── 自動執行，不攔截
    2. draft-reply（READONLY）── 自動執行，不攔截
    3. review-draft → Gate 1 暫停（REVERSIBLE_WRITE + privilege="prepare_send"）
    4. Gate 1 前：send-reply 副作用不發生
    5. Gate 1 核准 → run 繼續執行
    6. send-reply → Gate 2 暫停（IRREVERSIBLE_WRITE + privilege="dispatch"）
    7. Gate 2 前：send-reply 副作用仍未發生
    8. Gate 2 核准 → send-reply 真正執行，run 達 completed

    注意：使用獨立的 SQLite engine，只建立 agent_platform tables，
    避免 ForgeBase JSONB 欄位與 SQLite 的相容性問題。
    """
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
        ApprovalDecision, ApprovalDecisionRequest,
        SideEffectLevel, TaskCreateRequest, RunStatus,
    )
    from agent_platform.contracts import ProductCapabilities, StepExecutionResult

    # ── 建立只含 AgentOS tables 的 SQLite engine ──────────────────────────
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for tbl_cls in [
        TaskTable, PlanTable, StepTable, SessionTable,
        RunTable, RunStateTable, CheckpointTable, EvidenceTable,
        ApprovalTable, ToolCallTable,
    ]:
        tbl_cls.__table__.create(engine, checkfirst=True)

    class _FakeForgeBaseAdapter:
        def __init__(self):
            self.send_called = False

        @property
        def product_key(self):
            return "forgebase"

        def capabilities(self):
            return ProductCapabilities()

        async def execute_step(self, request):
            if request.step_name == "analyze-rfq":
                return StepExecutionResult(
                    output={"summary": "Buyer needs 200 units", "urgency": "medium"},
                    external_ref="a-gate-001",
                )
            if request.step_name == "draft-reply":
                return StepExecutionResult(
                    output={
                        "draft_id": "d-gate-001",
                        "subject": "Re: Your RFQ",
                        "body": "We can fulfil your order.",
                        "analysis_summary": "Buyer needs 200 units",
                    },
                    external_ref="d-gate-001",
                )
            if request.step_name == "review-draft":
                return StepExecutionResult(
                    output={"review_packet": {"draft": {"body": "We can fulfil your order."}}}
                )
            if request.step_name == "send-reply":
                self.send_called = True
                return StepExecutionResult(
                    output={"delivery_status": "queued"},
                    side_effects=["reply_dispatch_queued"],
                )
            raise AssertionError(f"Unexpected step: {request.step_name!r}")

    fake_adapter = _FakeForgeBaseAdapter()
    adapter_registry = build_default_adapter_registry()
    adapter_registry.replace(fake_adapter)

    service = WorkflowService(
        repository=SqlRepository(engine),
        adapter_registry=adapter_registry,
        workflow_registry=build_default_workflow_registry(),
        base_execution_policies=default_execution_policies(),
    )

    # ── 建立 task ─────────────────────────────────────────────────────────
    task_view = service.create_task(TaskCreateRequest(
        tenant_id="tenant-fb-gate-test",
        domain="forgebase_rfq",
        objective="Process RFQ for approval gate test",
        risk_level="medium",
        workflow_input={
            "rfq_id": "rfq-gate-001",
            "forgebase_base_url": "http://forgebase.local",
        },
    ))
    task_id = task_view.task.id

    # ── 驗 plan 中各步驟的 side_effect_level ─────────────────────────────
    plan = service.repository.get_plan(task_view.plan.id)
    steps_by_name = {s.name: s for s in plan.steps}

    for step_name in ("analyze-rfq", "draft-reply"):
        assert steps_by_name[step_name].side_effect_level == SideEffectLevel.READONLY, (
            f"步驟 {step_name!r} 應為 READONLY"
        )
    assert steps_by_name["review-draft"].side_effect_level == SideEffectLevel.REVERSIBLE_WRITE, (
        "review-draft 應為 REVERSIBLE_WRITE：草稿可修改，核准前不對外"
    )
    assert steps_by_name["send-reply"].side_effect_level == SideEffectLevel.IRREVERSIBLE_WRITE, (
        "send-reply 應為 IRREVERSIBLE_WRITE：回覆寄出後無法收回"
    )

    # ─────────────────────────────────────────────────────────────────────
    # Gate 1：review-draft
    # ─────────────────────────────────────────────────────────────────────
    run_view = service.run_task(task_id)

    assert run_view.run.status == RunStatus.WAITING_APPROVAL, (
        f"Gate 1：預期在 review-draft 暫停，實際 status={run_view.run.status!r}"
    )
    assert len(run_view.approvals) == 1, (
        f"Gate 1：預期 1 個 pending approval，實際 {len(run_view.approvals)} 個"
    )
    assert "review-draft" in run_view.run_state.summary, (
        f"Gate 1：run_state.summary={run_view.run_state.summary!r}，應含 'review-draft'"
    )

    # Gate 1 前：send-reply 副作用不應發生
    assert not fake_adapter.send_called, (
        "Gate 1 核准前，send-reply 的副作用不應發生"
    )

    gate1_approval_id = run_view.approvals[0].id
    run_id = run_view.run.id

    # Gate 1 核准
    after_gate1 = service.decide_approval(
        gate1_approval_id,
        ApprovalDecisionRequest(
            decision=ApprovalDecision.APPROVED,
            actor_id="sales-manager-review",
        ),
    )

    # ─────────────────────────────────────────────────────────────────────
    # Gate 2：send-reply（IRREVERSIBLE_WRITE）
    # ─────────────────────────────────────────────────────────────────────
    assert after_gate1.run.status == RunStatus.WAITING_APPROVAL, (
        f"Gate 2：Gate 1 核准後預期在 send-reply 暫停，"
        f"實際 status={after_gate1.run.status!r}"
    )

    # RunView.approvals 包含本次 run 的所有 approval（含已決定的）
    # 取出 PENDING 的那一個作為 Gate 2
    from agent_platform.models import ApprovalDecision as AD
    pending_approvals = [a for a in after_gate1.approvals if a.decision == AD.PENDING]
    assert len(pending_approvals) == 1, (
        f"Gate 2：預期 1 個 PENDING approval，實際 {len(pending_approvals)} 個"
    )
    assert "send-reply" in after_gate1.run_state.summary, (
        f"Gate 2：run_state.summary={after_gate1.run_state.summary!r}，應含 'send-reply'"
    )

    # Gate 2 前：send-reply 副作用仍不應發生
    assert not fake_adapter.send_called, (
        "Gate 2 核准前，send-reply 的副作用仍不應發生"
    )

    gate2_approval_id = pending_approvals[0].id

    # Gate 2 核准
    final_view = service.decide_approval(
        gate2_approval_id,
        ApprovalDecisionRequest(
            decision=ApprovalDecision.APPROVED,
            actor_id="sales-manager-dispatch",
        ),
    )

    # 兩次核准後：run 達 completed，send-reply 副作用發生
    assert final_view.run.status == RunStatus.COMPLETED, (
        f"兩次核准後 run 應為 completed，實際 {final_view.run.status!r}"
    )
    assert fake_adapter.send_called, (
        "兩次核准後 send-reply 應已執行"
    )

    # 驗：trace 包含完整生命週期（兩次 approval）
    trace_view = service.get_traces(run_id)
    event_types = [e.event_type for e in trace_view.events]
    assert event_types.count("approval.requested") == 2, (
        f"預期 2 次 approval.requested，實際 {event_types.count('approval.requested')} 次"
    )
    assert event_types.count("run.resumed") == 2, (
        f"預期 2 次 run.resumed，實際 {event_types.count('run.resumed')} 次"
    )
    assert "run.started" in event_types
    assert "run.completed" in event_types
