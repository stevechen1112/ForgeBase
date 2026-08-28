from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.core.config import settings
from app.services.email_service import EmailDeliveryResult
from scripts.run_controlled_email_probe import ControlledProbeError, run_probe


def _configure_safe_probe(monkeypatch) -> None:
    monkeypatch.setattr(
        settings,
        "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST",
        "steve_chen@premierbiz.com.tw",
    )
    monkeypatch.setattr(settings, "EMAIL_FROM", "steve_chen@premierbiz.com.tw")
    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", False)
    monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", False)
    monkeypatch.setattr(settings, "OUTREACH_SEND_ENABLED", False)
    monkeypatch.setattr(settings, "ESP_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "configured")
    monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", "configured")


@pytest.mark.asyncio
async def test_probe_confirms_provider_and_webhook_without_exposing_recipient(
    monkeypatch,
) -> None:
    _configure_safe_probe(monkeypatch)
    sender = AsyncMock(
        return_value=EmailDeliveryResult(
            True,
            True,
            False,
            "resend",
            message_id="provider-message-id",
        )
    )

    report = await run_probe(
        recipient="steve_chen@premierbiz.com.tw",
        probe_id="run-123",
        sender=sender,
        provider_lookup=AsyncMock(return_value="delivered"),
        webhook_lookup=AsyncMock(return_value={"sent", "delivered"}),
        sleeper=AsyncMock(),
    )
    rendered = str(report)

    assert report["assessment"]["status"] == "passed"
    assert report["assessment"]["provider_delivery_confirmed"] is True
    assert report["assessment"]["delivery_webhook_confirmed"] is True
    assert "steve_chen" not in rendered
    assert "provider-message-id" not in rendered
    assert sender.await_args.kwargs["recipient_kind"] == "internal"


@pytest.mark.asyncio
async def test_probe_never_opens_general_delivery_switches(monkeypatch) -> None:
    _configure_safe_probe(monkeypatch)
    monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", True)
    sender = AsyncMock()

    with pytest.raises(
        ControlledProbeError,
        match="general_delivery_switches_must_remain_closed",
    ):
        await run_probe(
            recipient="steve_chen@premierbiz.com.tw",
            probe_id="run-123",
            sender=sender,
        )

    sender.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "recipient",
    ["other@premierbiz.com.tw", "attacker@example.com", ""],
)
async def test_probe_rejects_non_exact_recipient(monkeypatch, recipient) -> None:
    _configure_safe_probe(monkeypatch)
    with pytest.raises(
        ControlledProbeError,
        match="recipient_not_exactly_internal_allowlisted",
    ):
        await run_probe(recipient=recipient, probe_id="run-123", sender=AsyncMock())


@pytest.mark.asyncio
async def test_probe_reports_missing_webhook_delivery(monkeypatch) -> None:
    _configure_safe_probe(monkeypatch)
    report = await run_probe(
        recipient="steve_chen@premierbiz.com.tw",
        probe_id="run-123",
        attempts=1,
        interval_seconds=0,
        sender=AsyncMock(
            return_value=EmailDeliveryResult(
                True,
                True,
                False,
                "resend",
                message_id="provider-message-id",
            )
        ),
        provider_lookup=AsyncMock(return_value="delivered"),
        webhook_lookup=AsyncMock(return_value=set()),
        sleeper=AsyncMock(),
    )

    assert report["assessment"]["status"] == "failed"
    assert report["assessment"]["blockers"] == [
        "delivery_webhook_not_observed"
    ]
