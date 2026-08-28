from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from app.core import encryption
from app.core.config import settings
from app.models.user import User
from cryptography.fernet import Fernet

from scripts import run_controlled_inbound_reply_probe as probe
from tests.conftest import _make_engine, requires_db


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


def test_controlled_probe_content_passes_the_real_outreach_guard() -> None:
    subject, text_body, html_body = probe._probe_content()
    cta = probe.canonical_cta("zh-TW")

    assert subject == "ForgeBase 真人回信閉環驗收（請回覆）"
    assert text_body.endswith(cta)
    assert text_body.count(cta) == 1
    assert "Reply-To" not in text_body
    assert html_body.count("<p>") == 2


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


@pytest.mark.parametrize(
    ("actor", "expected"),
    [
        (None, False),
        (SimpleNamespace(is_active=False, is_superuser=True, role="admin"), False),
        (SimpleNamespace(is_active=True, is_superuser=False, role="sales"), False),
        (SimpleNamespace(is_active=True, is_superuser=False, role="admin"), True),
        (SimpleNamespace(is_active=True, is_superuser=False, role="owner"), True),
        (SimpleNamespace(is_active=True, is_superuser=True, role="sales"), True),
    ],
)
def test_controlled_actor_must_be_an_active_privileged_operator(
    actor, expected: bool
) -> None:
    assert probe._actor_is_authorized(actor) is expected


class _SingleResult:
    def __init__(self, row) -> None:
        self.row = row

    def one_or_none(self):
        return self.row


class _TenantLookup:
    def __init__(self, row) -> None:
        self.row = row
        self.get_calls = []
        self.exec_calls = 0

    async def get(self, model, row_id):
        self.get_calls.append((model, row_id))
        return self.row

    async def exec(self, _query):
        self.exec_calls += 1
        return _SingleResult(self.row)


@pytest.mark.asyncio
async def test_controlled_tenant_prefers_actor_membership(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PUBLIC_TENANT_SLUG", "public-tenant")
    tenant = SimpleNamespace(is_active=True)
    db = _TenantLookup(tenant)
    actor = SimpleNamespace(tenant_id="actor-tenant-id")

    assert await probe._resolve_controlled_tenant(db, actor) is tenant
    assert db.get_calls == [(probe.Tenant, "actor-tenant-id")]
    assert db.exec_calls == 0


@pytest.mark.asyncio
async def test_system_admin_uses_configured_public_tenant(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PUBLIC_TENANT_SLUG", "public-tenant")
    tenant = SimpleNamespace(is_active=True)
    db = _TenantLookup(tenant)
    actor = SimpleNamespace(tenant_id=None)

    assert await probe._resolve_controlled_tenant(db, actor) is tenant
    assert db.exec_calls == 1


@pytest.mark.asyncio
async def test_system_admin_without_public_tenant_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(settings, "PUBLIC_TENANT_SLUG", "")
    db = _TenantLookup(None)
    actor = SimpleNamespace(tenant_id=None)

    with pytest.raises(
        probe.ControlledInboundProbeError,
        match="controlled_public_tenant_not_configured",
    ):
        await probe._resolve_controlled_tenant(db, actor)


def _session_context(factory):
    @asynccontextmanager
    async def context():
        async with factory() as session:
            yield session

    return context


@requires_db
@pytest.mark.asyncio
async def test_prepare_rows_persist_complete_controlled_journey(
    two_tenants, monkeypatch
) -> None:
    tenant, _other = two_tenants
    engine, factory = _make_engine()
    actor_email = f"controlled-{uuid.uuid4().hex[:10]}@test.invalid"
    recipient = f"reviewer-{uuid.uuid4().hex[:10]}@premierbiz.com.tw"
    probe_id = f"integration-{uuid.uuid4().hex[:16]}"
    monkeypatch.setattr(probe, "ACTOR_EMAIL", actor_email)
    monkeypatch.setattr(probe, "get_session_ctx", _session_context(factory))
    monkeypatch.setattr(
        settings,
        "ENCRYPTION_MASTER_KEY",
        Fernet.generate_key().decode().rstrip("="),
    )
    monkeypatch.setattr(encryption, "_fernet", None)
    try:
        async with factory() as db:
            db.add(
                User(
                    email=actor_email,
                    hashed_password="test",  # pragma: allowlist secret
                    role="admin",
                    is_active=True,
                    tenant_id=tenant.id,
                )
            )
            await db.commit()

        message = await probe._prepare_rows(recipient, probe_id)

        assert message.tenant_id == tenant.id
        assert message.send_idempotency_key == f"forgebase-inbound-probe:{probe_id}"
        assert message.status == "queued"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_prepare_reports_only_safe_stage_and_exception_type(monkeypatch) -> None:
    _ready(monkeypatch)

    async def fail_rows(_recipient: str, _probe_id: str):
        raise ValueError("must not appear in evidence: private@example.test")

    monkeypatch.setattr(probe, "_prepare_rows", fail_rows)
    with pytest.raises(
        probe.ControlledInboundProbeError,
        match="prepare_rows_unexpected_ValueError",
    ) as exc_info:
        await probe.prepare("reviewer@premierbiz.com.tw", "safe-probe")
    assert "private@example.test" not in str(exc_info.value)
