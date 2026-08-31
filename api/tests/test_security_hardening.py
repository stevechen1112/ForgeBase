from __future__ import annotations

from datetime import timedelta

import jwt

from app.core.security import create_access_token, decode_token


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
