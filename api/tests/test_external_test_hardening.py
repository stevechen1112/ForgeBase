import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest

from app.core.config import settings
from app.services import email_service
from app.services.external_test_readiness import external_test_readiness
from app.services.resend_webhook import verify_resend_signature
from app.api.v1.endpoints.webhooks import _should_add_suppression
from scripts.offsite_backup import decrypt, encrypt


@pytest.mark.asyncio
async def test_external_delivery_kill_switch_blocks_live_send(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", False)
    monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", False)
    monkeypatch.setattr(settings, "RESEND_API_KEY", "configured")

    result = await email_service.send_email_result(
        to="buyer@example.com",
        subject="must not send",
        recipient_kind="external",
    )

    assert result.delivered is False
    assert result.error == "external_delivery_disabled"


@pytest.mark.asyncio
async def test_internal_delivery_requires_allowlist(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_DRY_RUN", False)
    monkeypatch.setattr(settings, "EMAIL_INTERNAL_RECIPIENT_ALLOWLIST", "ops@example.com")
    monkeypatch.setattr(settings, "RESEND_API_KEY", "configured")

    result = await email_service.send_email_result(
        to="buyer@example.com",
        subject="must not send",
        recipient_kind="internal",
    )

    assert result.delivered is False
    assert result.error == "internal_recipient_not_allowlisted"


def test_resend_signature_verification_and_replay_window(monkeypatch):
    key = b"k" * 32
    secret = "whsec_" + base64.b64encode(key).decode()
    monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(settings, "RESEND_WEBHOOK_TOLERANCE_SECONDS", 300)
    raw = json.dumps({"type": "email.bounced", "data": {"to": ["a@example.com"]}}).encode()
    message_id = "msg_test"
    timestamp = str(int(time.time()))
    signed = f"{message_id}.{timestamp}.".encode() + raw
    signature = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
    headers = {
        "svix-id": message_id,
        "svix-timestamp": timestamp,
        "svix-signature": f"v1,{signature}",
    }

    assert verify_resend_signature(raw, headers) is True
    assert verify_resend_signature(raw + b" ", headers) is False
    headers["svix-timestamp"] = str(int(time.time()) - 301)
    assert verify_resend_signature(raw, headers) is False


def test_external_test_gate_reports_missing_resources_without_secrets(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_EXTERNAL_DELIVERY_ENABLED", False)
    monkeypatch.setattr(settings, "TURNSTILE_SECRET_KEY", "")
    monkeypatch.setattr(settings, "RESEND_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "BACKUP_S3_BUCKET_NAME", "")

    result = external_test_readiness()

    assert result["ready"] is False
    assert "turnstile" in result["blockers"]
    assert "resend_webhook" in result["blockers"]
    assert "offsite_backup" in result["blockers"]
    assert "SECRET" not in json.dumps(result)


def test_only_permanent_bounce_adds_local_suppression():
    permanent = {"data": {"bounce": {"type": "Permanent"}}}
    transient = {"data": {"bounce": {"type": "Transient"}}}

    assert _should_add_suppression("email.bounced", permanent) is True
    assert _should_add_suppression("email.bounced", transient) is False
    assert _should_add_suppression("email.complained", {}) is True


def test_offsite_backup_encryption_round_trip(monkeypatch, tmp_path: Path):
    key = base64.urlsafe_b64encode(b"e" * 32).decode()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    source = tmp_path / "database.sql.gz"
    encrypted = tmp_path / "database.sql.gz.enc"
    restored = tmp_path / "restored.sql.gz"
    source.write_bytes(b"forgebase backup\x00" * 1000)

    checksum = encrypt(source, encrypted)
    decrypt(encrypted, restored)

    assert restored.read_bytes() == source.read_bytes()
    assert checksum == hashlib.sha256(source.read_bytes()).hexdigest()
    assert source.read_bytes() not in encrypted.read_bytes()
