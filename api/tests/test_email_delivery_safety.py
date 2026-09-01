import uuid
from types import SimpleNamespace

import pytest
from app.core.config import settings
from app.services import email_service
from app.services.notifications import _rfq_email_body


@pytest.mark.asyncio
async def test_dry_run_is_successful_but_not_delivered(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", True)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_configured")

    result = await email_service.send_email_result(
        to="buyer@example.com",
        subject="test",
        text_body="body",
    )

    assert result.success is True
    assert result.delivered is False
    assert result.dry_run is True


@pytest.mark.asyncio
async def test_missing_key_is_not_reported_as_success(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", False)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "")

    result = await email_service.send_email_result(
        to="delivered@resend.dev",
        subject="test",
        recipient_kind="test",
    )

    assert result.success is False
    assert result.delivered is False
    assert result.error == "missing_api_key"


@pytest.mark.asyncio
async def test_resend_request_has_idempotency_and_no_secret_in_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        text = ""

        @staticmethod
        def json():
            return {"id": "email_123"}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, json, headers):
            captured.update(url=url, json=json, headers=headers)
            return FakeResponse()

    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", False)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "re_secret_value")
    monkeypatch.setattr(settings, "EMAIL_FROM", "notifications@example.org")
    monkeypatch.setattr(email_service.httpx, "AsyncClient", FakeClient)

    result = await email_service.send_email_result(
        to="delivered@resend.dev",
        subject="ForgeBase test",
        text_body="safe",
        idempotency_key="rfq-test-123",
        recipient_kind="test",
        message_headers={
            "List-Unsubscribe": "<https://example.org/unsubscribe/test>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
        provider_override="resend",
    )

    assert result.delivered is True
    assert result.message_id == "email_123"
    assert captured["headers"]["Idempotency-Key"] == "rfq-test-123"
    assert captured["headers"]["User-Agent"] == "ForgeBase/1.0"
    assert (
        captured["json"]["headers"]["List-Unsubscribe-Post"]
        == "List-Unsubscribe=One-Click"
    )
    assert "re_secret_value" not in repr(captured["json"])


def test_rfq_internal_email_escapes_contact_and_uses_configured_admin_url(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_URL", "https://pcbrm.tw/backend")
    rfq_id = uuid.uuid4()
    rfq = SimpleNamespace(
        id=rfq_id,
        rfq_number="RFQ-100",
        status="new",
        priority="high",
        created_at=SimpleNamespace(strftime=lambda _format: "2026-08-16 12:00 UTC"),
    )
    contact = SimpleNamespace(
        full_name="<script>alert(1)</script>",
        email="buyer@example.com",
        company_name="A & B",
    )

    body = _rfq_email_body(rfq, contact, "New RFQ")

    assert "<script>" not in body
    assert "&lt;script&gt;" in body
    assert "A &amp; B" in body
    assert f"https://pcbrm.tw/backend/dashboard/rfqs/{rfq_id}" in body
