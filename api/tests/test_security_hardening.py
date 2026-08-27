from __future__ import annotations

import pickle
from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_token
from app.services import ml_intent


def test_access_token_round_trip_and_algorithm_allowlist() -> None:
    token = create_access_token("security-user")
    payload = decode_token(token)

    assert payload is not None
    assert payload["sub"] == "security-user"
    assert payload["type"] == "access"

    unsigned = jwt.encode(
        {"sub": "attacker", "type": "access"}, key=None, algorithm="none"
    )
    assert decode_token(unsigned) is None


def test_expired_access_token_is_rejected() -> None:
    token = create_access_token("expired-user", expires_delta=timedelta(seconds=-1))
    assert decode_token(token) is None


def test_ml_model_requires_valid_service_hmac(monkeypatch, tmp_path) -> None:
    model_path = tmp_path / "intent.pkl"
    signature_path = tmp_path / "intent.pkl.sha256"
    metadata_path = tmp_path / "intent.json"
    payload = pickle.dumps({"trusted": True})
    model_path.write_bytes(payload)

    monkeypatch.setattr(ml_intent, "ML_MODEL_FILE", str(model_path))
    monkeypatch.setattr(ml_intent, "ML_MODEL_SIGNATURE_FILE", str(signature_path))
    monkeypatch.setattr(ml_intent, "ML_METADATA_FILE", str(metadata_path))
    monkeypatch.setattr(ml_intent, "_model_cache", None)
    monkeypatch.setattr(ml_intent, "_model_meta", {})

    assert ml_intent._load_model() is None

    signature_path.write_text("0" * 64, encoding="ascii")
    assert ml_intent._load_model() is None

    signature_path.write_bytes(b"\xff")
    assert ml_intent._load_model() is None

    expected = ml_intent._model_signature(payload)
    signature_path.write_text(expected, encoding="ascii")
    assert ml_intent._load_model() == {"trusted": True}
    assert expected != ml_intent._model_signature(payload + settings.SECRET_KEY.encode())
