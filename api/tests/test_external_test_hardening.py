import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
from app.api.v1.endpoints.webhooks import _should_add_suppression
from app.core.config import settings
from app.services import email_service
from app.services.external_test_readiness import external_test_readiness
from app.services.resend_webhook import verify_resend_signature
from cryptography.exceptions import InvalidTag
from scripts.offsite_backup import decrypt, encrypt

from scripts import offsite_backup


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
    secret = "whsec_" + base64.b64encode(key).decode()  # pragma: allowlist secret -- test fixture
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


def test_offsite_download_verifies_plaintext_checksum(monkeypatch, tmp_path: Path):
    key = base64.urlsafe_b64encode(b"k" * 32).decode()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setenv("BACKUP_S3_BUCKET_NAME", "private-backups")
    plaintext = tmp_path / "source.sql.gz"
    encrypted = tmp_path / "source.sql.gz.enc"
    destination = tmp_path / "restored" / "database.sql.gz"
    plaintext.write_bytes(b"verified backup" * 100)
    checksum = encrypt(plaintext, encrypted)

    class FakeS3:
        @staticmethod
        def head_object(*, Bucket, Key):
            assert Bucket == "private-backups"
            assert Key == "forgebase/database.sql.gz.enc"
            return {"Metadata": {"plaintext-sha256": checksum}}

        @staticmethod
        def download_file(bucket, object_key, target):
            assert bucket == "private-backups"
            assert object_key == "forgebase/database.sql.gz.enc"
            Path(target).write_bytes(encrypted.read_bytes())

    monkeypatch.setattr(offsite_backup, "client", lambda: FakeS3())
    offsite_backup.download("forgebase/database.sql.gz.enc", destination)

    assert destination.read_bytes() == plaintext.read_bytes()
    assert not destination.with_suffix(destination.suffix + ".enc").exists()


def test_offsite_download_rejects_bad_or_missing_checksum(monkeypatch, tmp_path: Path):
    key = base64.urlsafe_b64encode(b"k" * 32).decode()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setenv("BACKUP_S3_BUCKET_NAME", "private-backups")
    plaintext = tmp_path / "source.sql.gz"
    encrypted = tmp_path / "source.sql.gz.enc"
    destination = tmp_path / "database.sql.gz"
    plaintext.write_bytes(b"backup payload")
    encrypt(plaintext, encrypted)

    class FakeS3:
        metadata = {"plaintext-sha256": "0" * 64}

        @classmethod
        def head_object(cls, **_kwargs):
            return {"Metadata": cls.metadata}

        @staticmethod
        def download_file(_bucket, _object_key, target):
            Path(target).write_bytes(encrypted.read_bytes())

    monkeypatch.setattr(offsite_backup, "client", lambda: FakeS3())
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        offsite_backup.download("forgebase/database.sql.gz.enc", destination)
    assert not destination.exists()

    FakeS3.metadata = {}
    with pytest.raises(RuntimeError, match="missing a valid plaintext SHA-256"):
        offsite_backup.download("forgebase/database.sql.gz.enc", destination)

    FakeS3.metadata = {"plaintext-sha256": hashlib.sha256(plaintext.read_bytes()).hexdigest()}
    corrupted = bytearray(encrypted.read_bytes())
    corrupted[-17] ^= 1
    encrypted.write_bytes(corrupted)
    with pytest.raises(InvalidTag):
        offsite_backup.download("forgebase/database.sql.gz.enc", destination)
    assert not destination.exists()
