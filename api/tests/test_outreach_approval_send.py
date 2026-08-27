"""Batch-5 APPROVAL_SEND safety, idempotency and preference tests."""

import base64
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from app.core.config import settings
from app.core.datetime import utcnow_naive
from app.services.email_service import EmailDeliveryResult, _clean_message_headers
from app.services.outreach.delivery import _quiet_delay_seconds
from app.services.outreach.errors import OutreachSendRetryable
from app.services.outreach.events import apply_delivery_event
from app.services.outreach.unsubscribe import (
    InvalidUnsubscribeToken,
    issue_unsubscribe_token,
    verify_unsubscribe_token,
)
from app.services.resend_webhook import resend_webhook_signing_configured


def test_unsubscribe_token_is_signed_expiring_and_contains_no_email(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "OUTREACH_UNSUBSCRIBE_SECRET", "s" * 40)
    monkeypatch.setattr(settings, "OUTREACH_UNSUBSCRIBE_TOKEN_DAYS", 365)
    message_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    digest = "a" * 64
    token = issue_unsubscribe_token(
        message_id=message_id,
        tenant_id=tenant_id,
        email_hash=digest,
        scope="tenant",
    )
    assert "@" not in token
    claims = verify_unsubscribe_token(token)
    assert claims.message_id == message_id
    assert claims.tenant_id == tenant_id
    assert claims.email_hash == digest
    with pytest.raises(InvalidUnsubscribeToken):
        verify_unsubscribe_token(token[:-1] + ("A" if token[-1] != "A" else "B"))


def test_custom_headers_reject_injection_and_transport_override() -> None:
    assert _clean_message_headers({"List-Unsubscribe": "<https://example.test/u>"})
    with pytest.raises(ValueError):
        _clean_message_headers({"X-Test": "ok\r\nBcc: victim@example.test"})
    with pytest.raises(ValueError):
        _clean_message_headers({"To": "victim@example.test"})


def test_webhook_readiness_requires_a_valid_signing_secret(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", "not-base64")
    assert resend_webhook_signing_configured() is False
    monkeypatch.setattr(
        settings,
        "RESEND_WEBHOOK_SECRET",
        "whsec_" + base64.b64encode(b"w" * 32).decode(),
    )
    assert resend_webhook_signing_configured() is True


def test_delivery_projection_is_monotonic_for_out_of_order_events() -> None:
    now = utcnow_naive()
    message = SimpleNamespace(
        status="sent",
        sent_at=None,
        delivered_at=None,
        opened_at=None,
        clicked_at=None,
        bounced_at=None,
        complained_at=None,
        unsubscribed_at=None,
    )
    apply_delivery_event(message, "email.clicked", now)
    apply_delivery_event(message, "email.delivered", now - timedelta(minutes=1))
    apply_delivery_event(message, "email.opened", now - timedelta(minutes=2))
    assert message.status == "clicked"
    assert message.clicked_at == now
    assert message.delivered_at == now - timedelta(minutes=1)
    apply_delivery_event(message, "email.complained", now + timedelta(minutes=1))
    apply_delivery_event(message, "email.clicked", now + timedelta(minutes=2))
    assert message.status == "complained"


def test_quiet_hours_compute_next_open_without_sleep() -> None:
    from app.models.outreach import OutreachDeliveryPolicy

    policy = OutreachDeliveryPolicy(
        tenant_id=uuid.uuid4(),
        timezone="UTC",
        quiet_hours_enabled=True,
        quiet_start_hour=20,
        quiet_end_hour=8,
    )
    delay = _quiet_delay_seconds(
        policy, utcnow_naive().replace(hour=23, minute=0, second=0, microsecond=0)
    )
    assert delay == 9 * 60 * 60
    assert _quiet_delay_seconds(policy, utcnow_naive().replace(hour=12)) == 0


def test_retryable_delivery_result_contract() -> None:
    failure = EmailDeliveryResult(False, False, False, "resend", error="request_failed")
    assert failure.message_id is None
    error = OutreachSendRetryable(failure.error or "failed")
    assert error.retry_after_seconds == 120
