import json
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlmodel import select

from app.core.datetime import utcnow_naive
from app.core.security import decode_token
from app.models.copilot_conversation import CopilotConversation
from app.models.notification_preference import NotificationPreference
from app.services.copilot import chat_engine
from app.services.copilot.chat_engine import CopilotEngine
from app.api.v1.endpoints import copilot as copilot_endpoints
from tests.conftest import _make_engine, requires_db


class _FakeToolCall:
    def __init__(self, call_id: str, name: str, arguments: str):
        self.id = call_id
        self.function = SimpleNamespace(name=name, arguments=arguments)


class _FakeMessage:
    def __init__(self, *, content: str | None = None, tool_calls: list[_FakeToolCall] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none: bool = True) -> dict:
        payload = {"role": "assistant"}
        if self.content is not None or not exclude_none:
            payload["content"] = self.content
        if self.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return payload


class _FakeResponse:
    def __init__(self, message: _FakeMessage):
        self.choices = [SimpleNamespace(message=message)]


@pytest.mark.asyncio
async def test_copilot_engine_runs_tool_loop_and_persists_history(monkeypatch):
    completions_calls = 0

    async def fake_create(**kwargs):
        nonlocal completions_calls
        completions_calls += 1
        if completions_calls == 1:
            return _FakeResponse(
                _FakeMessage(
                    tool_calls=[
                        _FakeToolCall("tool-1", "get_dashboard_stats", '{"hours": 24}')
                    ]
                )
            )
        return _FakeResponse(_FakeMessage(content="整理完成的業務摘要"))

    monkeypatch.setattr(
        chat_engine,
        "_openai",
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))),
    )

    saved_messages: list[tuple[str, str, str | None]] = []
    executed_tools: list[tuple[str, str]] = []

    async def fake_build_company_context(self):
        return "- **Brand / Company**: ForgeBase"

    async def fake_load_history(self):
        return [{"role": "assistant", "content": "上一輪摘要"}]

    async def fake_save_message(self, role: str, content: str, tool_calls_json: str | None = None):
        saved_messages.append((role, content, tool_calls_json))

    async def fake_execute_tool(self, name: str, arguments_str: str) -> str:
        executed_tools.append((name, arguments_str))
        return '{"new_rfqs_in_period": 3}'

    monkeypatch.setattr(CopilotEngine, "_build_company_context", fake_build_company_context)
    monkeypatch.setattr(CopilotEngine, "_load_history", fake_load_history)
    monkeypatch.setattr(CopilotEngine, "_save_message", fake_save_message)
    monkeypatch.setattr(CopilotEngine, "_execute_tool", fake_execute_tool)

    engine = CopilotEngine(
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        channel="web",
        channel_user_id="user-123",
    )

    chunks = await engine.run("今天有幾個新 RFQ？")

    assert chunks == ["整理完成的業務摘要"]
    assert completions_calls == 2
    assert executed_tools == [("get_dashboard_stats", '{"hours": 24}')]
    assert saved_messages[0] == ("user", "今天有幾個新 RFQ？", None)
    assert saved_messages[1][0] == "assistant"
    assert saved_messages[1][1] == "整理完成的業務摘要"
    assert json.loads(saved_messages[1][2]) == [
        {
            "id": "tool-1",
            "type": "function",
            "function": {
                "name": "get_dashboard_stats",
                "arguments": '{"hours": 24}',
            },
        }
    ]


@requires_db
@pytest.mark.asyncio
async def test_telegram_bind_start_updates_existing_chat_id_and_disables_binding(
    http_client,
    two_tenants,
    admin_token_for_tenant,
    monkeypatch,
):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    user_id = uuid.UUID(decode_token(token)["sub"])
    engine, factory = _make_engine()

    try:
        async with factory() as session:
            session.add(
                NotificationPreference(
                    user_id=user_id,
                    tenant_id=tenant_a.id,
                    channel="telegram",
                    channel_config=json.dumps({"chat_id": "old-chat"}),
                    enabled=True,
                )
            )
            await session.commit()

        async def fake_send_binding_code(chat_id: str, code: str) -> bool:
            assert chat_id == "@new_chat_id"
            assert len(code) == 6
            return True

        monkeypatch.setattr(copilot_endpoints._telegram, "send_binding_code", fake_send_binding_code)

        response = await http_client.post(
            "/api/v1/copilot/telegram/bind-start",
            headers={"Authorization": f"Bearer {token}"},
            json={"telegram_chat_id": "  @new_chat_id  "},
        )

        assert response.status_code == 200

        async with factory() as session:
            pref = (
                await session.exec(
                    select(NotificationPreference)
                    .where(NotificationPreference.user_id == user_id)
                    .where(NotificationPreference.channel == "telegram")
                )
            ).first()

            assert pref is not None
            assert json.loads(pref.channel_config) == {"chat_id": "@new_chat_id"}
            assert pref.enabled is False
            assert pref.binding_code is not None
            assert pref.binding_code_expires_at is not None
    finally:
        await engine.dispose()


@requires_db
@pytest.mark.asyncio
async def test_web_chat_history_excludes_tool_messages_and_respects_limit(
    http_client,
    two_tenants,
    admin_token_for_tenant,
):
    tenant_a, _ = two_tenants
    token = await admin_token_for_tenant(tenant_a.id)
    user_id = uuid.UUID(decode_token(token)["sub"])
    engine, factory = _make_engine()
    base_time = utcnow_naive()

    try:
        async with factory() as session:
            session.add_all(
                [
                    CopilotConversation(
                        user_id=user_id,
                        tenant_id=tenant_a.id,
                        channel="web",
                        channel_user_id=str(user_id),
                        role="user",
                        content="第一則使用者訊息",
                        created_at=base_time,
                    ),
                    CopilotConversation(
                        user_id=user_id,
                        tenant_id=tenant_a.id,
                        channel="web",
                        channel_user_id=str(user_id),
                        role="tool",
                        content='{"internal": true}',
                        created_at=base_time + timedelta(seconds=1),
                    ),
                    CopilotConversation(
                        user_id=user_id,
                        tenant_id=tenant_a.id,
                        channel="web",
                        channel_user_id=str(user_id),
                        role="assistant",
                        content="第二則助理訊息",
                        created_at=base_time + timedelta(seconds=2),
                    ),
                    CopilotConversation(
                        user_id=user_id,
                        tenant_id=tenant_a.id,
                        channel="web",
                        channel_user_id=str(user_id),
                        role="user",
                        content="第三則使用者訊息",
                        created_at=base_time + timedelta(seconds=3),
                    ),
                ]
            )
            await session.commit()

        response = await http_client.get(
            "/api/v1/copilot/chat/history?limit=2",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["data"] == [
            {
                "id": response.json()["data"][0]["id"],
                "role": "assistant",
                "content": "第二則助理訊息",
                "created_at": response.json()["data"][0]["created_at"],
            },
            {
                "id": response.json()["data"][1]["id"],
                "role": "user",
                "content": "第三則使用者訊息",
                "created_at": response.json()["data"][1]["created_at"],
            },
        ]
    finally:
        await engine.dispose()