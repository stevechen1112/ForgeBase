"""
TDD: ForgeBase Content Generation auto-trigger 條件一 — 正向 & 負向驗證

Acceptance Criteria (Condition 1 - Auto-trigger):

正向驗證 (test_forgebase_content_auto_trigger):
- POST /api/v1/content/generate 被呼叫時，ForgeBase 自動呼叫 AgentOS POST /tasks
- AgentOS 返回 run_id
- run_id 自動儲存到 PageBrief.agent_run_id
- 查詢 GET /api/v1/content/briefs/{id} 返回 agent_run_id

負向驗證 (test_forgebase_content_auto_trigger_agentOS_unavailable):
- AgentOS 無回應 / ConnectError
- 內容生成仍然成功（核心業務不中斷）
- PageBrief.agent_run_id 為 null
- 錯誤被記錄到 log

Run:
    pytest tests/test_forgebase_content_auto_trigger.py -v
"""

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient, ConnectError

from app.core.config import settings
from app.models.page_brief import PageBrief
from app.models.user import User
from tests.conftest import _make_engine

pytestmark: list = []

# ─────────────────────────────────────────────────────────────────────────────
# Constants & Fake Data
# ─────────────────────────────────────────────────────────────────────────────

_TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")

FAKE_AGENTOSS_TASK_ID = "task-content-abc123"
FAKE_AGENTOSS_RUN_ID = "run-content-xyz789"

_AGENTOSS_SUCCESS_RESPONSE = {
    "task": {"id": FAKE_AGENTOSS_TASK_ID, "status": "pending"},
    "run": {"id": FAKE_AGENTOSS_RUN_ID, "status": "running"},
}

_FAKE_GENERATE_RESULT = {
    "title": "Test Article Title",
    "body": "Test content body",
    "meta_description": "Test meta description",
}


@asynccontextmanager
async def _service_test_session_ctx():
    """Use test DB sessions inside app.services.agentOS to avoid cross-loop pool issues."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            yield db
    finally:
        await eng.dispose()


async def _ensure_test_user() -> None:
    """Insert test admin user into DB if not present (required for AIGenerationLog FK)."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            existing = await db.get(User, _TEST_USER_ID)
            if not existing:
                user = User(
                    id=_TEST_USER_ID,
                    email="test-content-admin@agentos-test.com",
                    hashed_password="!",
                    full_name="Test Admin",
                    role="admin",
                    is_active=True,
                    tenant_id=None,
                )
                db.add(user)
                await db.commit()
    finally:
        await eng.dispose()


async def _create_approved_brief() -> uuid.UUID:
    """Insert a PageBrief with brief_status='approved' into DB. Returns brief_id."""
    eng, factory = _make_engine()
    try:
        async with factory() as db:
            brief = PageBrief(
                target_page_type="product",
                target_slug="test-product",
                title_draft="Test Product Page",
                primary_keyword="test keyword",
                brief_status="approved",
                ai_status="pending",
                locale="en",
                created_by=_TEST_USER_ID,
                tenant_id=None,
            )
            db.add(brief)
            await db.commit()
            await db.refresh(brief)
            return brief.id
    finally:
        await eng.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgebase_content_auto_trigger(http_client: AsyncClient):
    """
    正向驗證：POST /api/v1/content/generate → AgentOS 自動觸發 → agent_run_id 存入 PageBrief
    """
    await _ensure_test_user()
    brief_id = await _create_approved_brief()

    agentOS_task_url = f"{settings.AGENTOSS_URL}/tasks"
    original_post = httpx.AsyncClient.post
    agentOS_calls = []

    async def selective_post(self, url, *args, **kwargs):
        url_str = str(url)
        if url_str == agentOS_task_url or settings.AGENTOSS_URL in url_str:
            agentOS_calls.append({"url": url_str, "json": kwargs.get("json")})
            return httpx.Response(
                status_code=200,
                json=_AGENTOSS_SUCCESS_RESPONSE,
                request=httpx.Request("POST", url_str),
            )
        return await original_post(self, url, *args, **kwargs)

    from app.main import app
    from app.api.v1.deps import get_current_user

    mock_user = User(
        id=_TEST_USER_ID,
        email="test-content-admin@agentos-test.com",
        hashed_password="!",
        full_name="Test Admin",
        role="admin",
        is_active=True,
        tenant_id=None,
    )

    async def _override_user():
        return mock_user

    app.dependency_overrides[get_current_user] = _override_user

    try:
        with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
             patch.object(httpx.AsyncClient, "post", new=selective_post), \
             patch("app.api.v1.endpoints.ai_generate.generate_content", new=AsyncMock(return_value=_FAKE_GENERATE_RESULT)):

            response = await http_client.post(
                "/api/v1/content/generate",
                json={"brief_id": str(brief_id)},
            )

            assert response.status_code in (200, 201), (
                f"Content generate failed: {response.status_code} {response.text}"
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # AgentOS が呼ばれたことを確認
    assert len(agentOS_calls) >= 1, "AgentOS POST /tasks was not called"
    call = agentOS_calls[0]
    payload = call["json"]
    assert payload["domain"] == "forgebase_ai_content"
    assert str(brief_id) in payload.get("idempotency_key", "")

    # DB で agent_run_id が保存されたことを確認
    eng, factory = _make_engine()
    async with factory() as db:
        brief = await db.get(PageBrief, brief_id)
    await eng.dispose()

    assert brief is not None
    assert brief.agent_run_id == FAKE_AGENTOSS_RUN_ID, (
        f"Expected agent_run_id={FAKE_AGENTOSS_RUN_ID!r}, got {brief.agent_run_id!r}"
    )

    # API 경유로도 확인 (GET /api/v1/content/briefs/{id})
    app.dependency_overrides[get_current_user] = _override_user
    try:
        get_resp = await http_client.get(f"/api/v1/content/briefs/{brief_id}")
        assert get_resp.status_code == 200
        brief_data = get_resp.json()
        # CRUD router wraps response: {"data": {...}, "meta": ...}
        brief_obj = brief_data.get("data") or brief_data
        assert brief_obj.get("agent_run_id") == FAKE_AGENTOSS_RUN_ID
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_forgebase_content_auto_trigger_agentOS_unavailable(http_client: AsyncClient):
    """
    負向驗證：AgentOS 無回應 → 內容生成仍成功 → agent_run_id 為 null
    """
    await _ensure_test_user()
    brief_id = await _create_approved_brief()

    from app.main import app
    from app.api.v1.deps import get_current_user

    mock_user = User(
        id=_TEST_USER_ID,
        email="test-content-admin@agentos-test.com",
        hashed_password="!",
        full_name="Test Admin",
        role="admin",
        is_active=True,
        tenant_id=None,
    )

    async def _override_user():
        return mock_user

    original_post_neg = httpx.AsyncClient.post

    async def agentOS_unavailable(self, url, *args, **kwargs):
        url_str = str(url)
        if settings.AGENTOSS_URL in url_str:
            raise ConnectError("AgentOS unreachable", request=httpx.Request("POST", url_str))
        return await original_post_neg(self, url, *args, **kwargs)

    app.dependency_overrides[get_current_user] = _override_user

    try:
        with patch("app.services.agentOS.get_session_ctx", new=_service_test_session_ctx), \
             patch.object(httpx.AsyncClient, "post", new=agentOS_unavailable), \
             patch("app.api.v1.endpoints.ai_generate.generate_content", new=AsyncMock(return_value=_FAKE_GENERATE_RESULT)):

            response = await http_client.post(
                "/api/v1/content/generate",
                json={"brief_id": str(brief_id)},
            )

            # 核心業務不能因為 AgentOS 無回應而失敗
            assert response.status_code in (200, 201), (
                f"Content generation should succeed even when AgentOS is unavailable: "
                f"{response.status_code} {response.text}"
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # agent_run_id 應為 null
    eng, factory = _make_engine()
    async with factory() as db:
        brief = await db.get(PageBrief, brief_id)
    await eng.dispose()

    assert brief is not None
    assert brief.agent_run_id is None, (
        f"agent_run_id should be null when AgentOS unavailable, got {brief.agent_run_id!r}"
    )
