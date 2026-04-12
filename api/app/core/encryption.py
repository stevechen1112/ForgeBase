"""
Symmetric encryption for integration credentials.

Uses Fernet (AES-128-CBC + HMAC-SHA256).
The master key must be a URL-safe base64-encoded 32-byte key stored in
ENCRYPTION_MASTER_KEY env var.  Generate one with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

If ENCRYPTION_MASTER_KEY is empty the module falls back to a *deterministic*
dev key derived from SECRET_KEY — this is safe for local dev but should NEVER
be used in production.
"""
from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet  # noqa: PLW0603
    if _fernet is not None:
        return _fernet

    from app.core.config import settings  # lazy import to avoid circular deps

    raw = settings.ENCRYPTION_MASTER_KEY
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
    else:
        if settings.is_production:
            raise RuntimeError(
                "ENCRYPTION_MASTER_KEY must be set in production. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        # Dev fallback: derive a 32-byte key from SECRET_KEY
        logger.warning(
            "ENCRYPTION_MASTER_KEY not set — using dev fallback derived from SECRET_KEY. "
            "Set a proper key in production!"
        )
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)

    _fernet = Fernet(key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return a URL-safe token string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token and return the plaintext string."""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Credential decryption failed — key mismatch or corrupted data") from exc
