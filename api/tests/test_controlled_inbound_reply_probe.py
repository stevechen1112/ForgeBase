from __future__ import annotations

import json

import pytest
from app.core.config import settings

from scripts import run_controlled_inbound_reply_probe as probe


def _ready(monkeypatch) -> None:
    monkeypatch.setattr(
        settings, "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST", "reviewer@premierbiz.com.tw"
    )
    monkeypatch.setattr(settings, "EMAIL_FROM", "reviewer@premierbiz.com.tw")
    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", False)
    monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", True)
    monkeypatch.setattr(settings, "OUTREACH_SEND_ENABLED", True)
    monkeypatch.setattr(settings, "INBOUND_REPLY_ENABLED", True)
    monkeypatch.setattr(settings, "ESP_PROVIDER", "resend")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "test-resend-key")
    monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_DOMAIN", probe.INBOUND_DOMAIN)
    monkeypatch.setattr(settings, "OUTREACH_INBOUND_SECRET", "r" * 40)


def test_prepare_validation_accepts_only_exact_internal_controlled_address(
    monkeypatch,
) -> None:
    _ready(monkeypatch)
    assert (
        probe._validate_prepare("reviewer@premierbiz.com.tw", "33155399573")
        == "reviewer@premierbiz.com.tw"
    )
    with pytest.raises(
        probe.ControlledInboundProbeError,
        match="recipient_not_exactly_internal_allowlisted",
    ):
        probe._validate_prepare("external@example.com", "33155399573")


@pytest.mark.parametrize(
    ("setting", "value", "reason"),
    [
        (
            "EMAIL_EXTERNAL_DELIVERY_ENABLED",
            False,
            "process_scoped_probe_switches_not_enabled",
        ),
        ("OUTREACH_SEND_ENABLED", False, "process_scoped_probe_switches_not_enabled"),
        ("INBOUND_REPLY_ENABLED", False, "process_scoped_probe_switches_not_enabled"),
        (
            "OUTREACH_INBOUND_DOMAIN",
            "wrong.example.test",
            "inbound_domain_not_expected",
        ),
        ("OUTREACH_INBOUND_SECRET", "short", "inbound_route_secret_missing"),
    ],
)
def test_prepare_validation_fails_closed(
    monkeypatch, setting: str, value, reason: str
) -> None:
    _ready(monkeypatch)
    monkeypatch.setattr(settings, setting, value)
    with pytest.raises(probe.ControlledInboundProbeError, match=reason):
        probe._validate_prepare("reviewer@premierbiz.com.tw", "33155399573")


def test_failure_report_never_contains_contact_or_credentials() -> None:
    report = probe._failure_report("prepare", "safe_failure")
    assert report["assessment"] == {
        "status": "failed",
        "blockers": ["safe_failure"],
    }
    assert not any(report["privacy"].values())


def test_report_can_be_streamed_without_container_temp_file(capsys) -> None:
    report = probe._failure_report("status", "safe_failure")

    probe._write_report(report, "-")

    assert json.loads(capsys.readouterr().out) == report


def test_report_can_still_be_written_to_a_file(tmp_path) -> None:
    report = probe._failure_report("status", "safe_failure")
    output = tmp_path / "probe.json"

    probe._write_report(report, str(output))

    assert json.loads(output.read_text(encoding="utf-8")) == report
