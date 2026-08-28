from __future__ import annotations

import base64
import secrets

import pytest
from app.core import config, encryption
from app.core.config import settings
from cryptography.fernet import Fernet


def test_canonical_fernet_key_is_preserved() -> None:
    key = Fernet.generate_key()

    assert encryption.normalize_fernet_key(key) == key


def test_missing_base64_padding_is_normalized() -> None:
    raw = secrets.token_urlsafe(32)
    assert len(base64.urlsafe_b64decode(raw + "=")) == 32

    normalized = encryption.normalize_fernet_key(raw)

    assert len(normalized) == 44
    assert len(base64.urlsafe_b64decode(normalized)) == 32


@pytest.mark.parametrize(
    "value",
    ["", "not-base64!", "c2hvcnQ=", Fernet.generate_key().decode() + "!"],
)
def test_invalid_encryption_keys_are_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="Encryption key"):
        encryption.normalize_fernet_key(value)


def test_encrypt_decrypt_accepts_unpadded_production_style_key(monkeypatch) -> None:
    key = Fernet.generate_key().decode().rstrip("=")
    monkeypatch.setattr(settings, "ENCRYPTION_MASTER_KEY", key)
    monkeypatch.setattr(encryption, "_fernet", None)

    token = encryption.encrypt("internal-reviewer@example.test")

    assert encryption.decrypt(token) == "internal-reviewer@example.test"
    monkeypatch.setattr(encryption, "_fernet", None)


def _production_ready(monkeypatch, encryption_key: str) -> None:
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "APP_URL", "https://api.example.test")
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://www.example.test")
    monkeypatch.setattr(settings, "ADMIN_URL", "https://admin.example.test")
    monkeypatch.setattr(settings, "ALLOWED_ORIGINS", "https://admin.example.test")
    monkeypatch.setattr(settings, "ENCRYPTION_MASTER_KEY", encryption_key)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(settings, "CHAT_ENABLED", False)


def test_production_startup_accepts_unpadded_key(monkeypatch) -> None:
    _production_ready(monkeypatch, Fernet.generate_key().decode().rstrip("="))

    config._validate_production_settings()


def test_production_startup_rejects_malformed_key(monkeypatch) -> None:
    _production_ready(monkeypatch, "malformed")

    with pytest.raises(RuntimeError, match="URL-safe base64-encoded 32-byte"):
        config._validate_production_settings()
