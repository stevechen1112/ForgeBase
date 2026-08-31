"""T5/T6/T8：即時推播、自動確認信、首回統計。"""
import json
import uuid
from unittest.mock import AsyncMock, patch

from app.services.rfq_auto_reply import (
    build_ack_email,
    compute_missing_info,
    seconds_until_business_open,
)
from tests.conftest import requires_db


# ── T5：LINE channel payload ─────────────────────────────────────────────

async def test_line_channel_payload_and_missing_token():
    from app.services.channels import line as line_mod

    channel = line_mod.LineChannel()

    # 無 token → False 且不發送
    with patch.object(line_mod, "LINE_CHANNEL_ACCESS_TOKEN", ""):
        assert await channel.send({"line_user_id": "U123"}, "hello") is False

    captured = {}

    class _Resp:
        status_code = 200
        text = "{}"

    async def _post(url, *, json=None, headers=None, **kw):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _Resp()

    with patch.object(line_mod, "LINE_CHANNEL_ACCESS_TOKEN", "test-token"), \
         patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=_post)):
        ok = await channel.send(
            {"line_user_id": "U123"},
            "New RFQ arrived",
            buttons=[{"label": "查看", "url": "https://example.com/rfq/1"}],
        )

    assert ok is True
    assert captured["url"].endswith("/bot/message/push")
    assert captured["json"]["to"] == "U123"
    assert captured["headers"]["Authorization"] == "Bearer test-token"
    msg = captured["json"]["messages"][0]
    assert msg["type"] == "template"
    assert msg["template"]["actions"][0]["uri"] == "https://example.com/rfq/1"


# ── T6：確認信內容與缺口清單 ─────────────────────────────────────────────

def test_missing_info_checklist():
    full = {
        "quantity": "10k pcs", "specifications": "SUS304 per DIN",
        "incoterm": "FOB", "required_certs": ["CE"], "timeline": "1-3 months",
    }
    assert compute_missing_info(full) == []

    empty = {}
    missing = compute_missing_info(empty)
    assert len(missing) == 4  # 最多列四項
    assert any("quantity" in m.lower() for m in missing)


def test_ack_email_professional_and_escaped():
    subject, body = build_ack_email(
        rfq_number="RFQ-20260803-001",
        form={
            "full_name": "Hans <b>Müller</b>",
            "quantity": "10,000 pcs",
            "specifications": "SUS304, tolerance +/-0.05mm",
        },
        missing_info=["Preferred trade terms (e.g. FOB, CIF, DAP)"],
        sla_hours=4,
        signature="Alice Wang\nExport Sales",
        company_display="Acme Fasteners",
    )
    assert "RFQ-20260803-001" in subject
    assert "within 4 business hours" in body
    assert "Hans &lt;b&gt;Müller&lt;/b&gt;" in body  # XSS escape
    assert "10,000 pcs" in body
    assert "trade terms" in body
    assert "Alice Wang" in body


def test_business_open_delay():
    # 週一 09:00 CEST（07:00 UTC）→ 已在上班時段，delay 0
    assert seconds_until_business_open("Europe/Berlin", __import__("datetime").datetime(2026, 8, 3, 7, 0)) == 0.0
    # 週六 → 大於 0
    assert seconds_until_business_open("Europe/Berlin", __import__("datetime").datetime(2026, 8, 1, 10, 0)) > 0


# ── T6：開關行為（DB）────────────────────────────────────────────────────

@requires_db
async def test_auto_reply_respects_tenant_toggle(http_client, two_tenants):
    """關閉的 tenant 不發信；開啟的 tenant 會寫入 auto_reply_sent 事件。

    端點本身也會觸發 maybe_auto_reply（背景 task），測試時先把端點觸發
    mock 掉，再以真實函式直接驗證 gate／發送／冪等。
    """
    from sqlalchemy import text as sa_text
    from tests.conftest import _make_engine

    tenant_a, tenant_b = two_tenants
    eng, factory = _make_engine()

    # tenant_b 開啟 auto reply（直接在 DB 建 site profile）
    from app.models.site_profile import SiteProfile
    async with factory() as session:
        session.add(SiteProfile(
            tenant_id=tenant_b.id,
            site_url=f"https://b-{uuid.uuid4().hex[:6]}.example.com",
            ops_config_json=json.dumps({"auto_reply_enabled": True, "auto_reply_signature": "Bob\nSales"}),
        ))
        await session.commit()

    def payload(email, country="DE"):
        return {
            "full_name": "Buyer", "email": email, "company_name": "Acme",
            "country": country, "consent": True, "product_ids": [],
            "quantity": "10k pcs", "specifications": "SUS304 per DIN EN 10088 standard",
            "incoterm": "FOB", "timeline": "1-3 months",
        }

    sent_emails = []

    async def _fake_send(to, subject, html_body=None, text_body=None, from_name=None, **kw):
        from app.services.email_service import EmailDeliveryResult

        sent_emails.append({"to": to, "subject": subject})
        return EmailDeliveryResult(
            success=True,
            delivered=True,
            dry_run=False,
            provider="test",
            message_id="test-message",
        )

    from app.services import rfq_auto_reply as auto_mod
    real_maybe = auto_mod.maybe_auto_reply
    endpoint_trigger = AsyncMock()

    # 1) 端點觸發 mock：驗證 submit_rfq 確實有接上 auto-reply 管線
    with patch.object(auto_mod, "maybe_auto_reply", new=endpoint_trigger):
        r = await http_client.post(
            "/api/v1/forms/rfq", json=payload(f"a-{uuid.uuid4().hex[:6]}@acme.com"),
            headers={"X-Tenant-ID": str(tenant_a.id)},
        )
        assert r.status_code == 201, r.text
        rfq_a = r.json()["rfq_id"]
        r = await http_client.post(
            "/api/v1/forms/rfq", json=payload(f"b-{uuid.uuid4().hex[:6]}@acme.com"),
            headers={"X-Tenant-ID": str(tenant_b.id)},
        )
        assert r.status_code == 201, r.text
        rfq_b = r.json()["rfq_id"]

    # Endpoint now writes a durable outbox job for each tenant instead of a
    # fire-and-forget coroutine; the per-tenant gate remains inside the worker.
    assert endpoint_trigger.await_count == 0
    async with factory() as session:
        queued = (await session.exec(
            sa_text(
                "SELECT count(*) FROM operational_jobs "
                "WHERE job_type = 'rfq_auto_reply' AND idempotency_key IN (:a, :b)"
            ),
            params={"a": f"rfq:{rfq_a}:auto-reply", "b": f"rfq:{rfq_b}:auto-reply"},
        )).scalar()
        assert queued == 2

    # 2) 真實函式直接驗證
    with patch("app.services.email_service.send_email_result", new=AsyncMock(side_effect=_fake_send)):
        # tenant_a（未開啟）→ 不發
        assert await real_maybe(uuid.UUID(rfq_a), tenant_a.id) is False
        assert sent_emails == []

        # tenant_b（開啟）→ 發送（買家上班時段檢查 mock 成立即）
        with patch("app.services.rfq_auto_reply.seconds_until_business_open", return_value=0.0):
            assert await real_maybe(uuid.UUID(rfq_b), tenant_b.id) is True
            # 冪等：第二次不再發
            assert await real_maybe(uuid.UUID(rfq_b), tenant_b.id) is False

    assert len(sent_emails) == 1
    assert "RFQ-" in sent_emails[0]["subject"]

    # 事件與首回時間有記錄
    async with factory() as session:
        rows = (await session.exec(
            sa_text("SELECT event_type FROM rfq_events WHERE rfq_id = :rid"),
            params={"rid": rfq_b},
        )).all()
        assert any(r[0] == "auto_reply_sent" for r in rows)
        frt = (await session.exec(
            sa_text("SELECT first_response_at FROM rfq_requests WHERE id = :rid"),
            params={"rid": rfq_b},
        )).scalar()
        assert frt is not None

    await eng.dispose()


# ── T8：首回統計 endpoint ────────────────────────────────────────────────

@requires_db
async def test_rfq_stats_endpoint(http_client, two_tenants, admin_token_for_tenant):
    tenant_a, _ = two_tenants
    tag = uuid.uuid4().hex[:8]
    headers = {"X-Tenant-ID": str(tenant_a.id)}

    r = await http_client.post("/api/v1/forms/rfq", headers=headers, json={
        "full_name": "Stats Buyer", "email": f"stats-{tag}@acme.com",
        "company_name": "Acme", "country": "DE", "consent": True, "product_ids": [],
    })
    assert r.status_code == 201, r.text
    rfq_id = r.json()["rfq_id"]

    token = await admin_token_for_tenant(tenant_a.id)
    auth = {"Authorization": f"Bearer {token}"}

    await http_client.put(
        f"/api/v1/tracking/rfqs/{rfq_id}/status", headers=auth,
        json={"status": "in_progress"},
    )

    r = await http_client.get("/api/v1/tracking/rfqs/stats?days=30", headers=auth)
    assert r.status_code == 200, r.text
    stats = r.json()
    assert stats["total_rfqs"] >= 1
    assert stats["responded"] >= 1
    assert stats["avg_first_response_hours"] is not None
    assert stats["sla_applicable"] >= 1
    assert "sla_achievement_rate" in stats
