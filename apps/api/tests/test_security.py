"""Unit tests for password hashing and JWT session tokens (app.core.security)."""

import uuid

import jwt
import pytest

from app.core import security


def test_password_hash_round_trip():
    hashed = security.hash_password("correct horse battery staple")

    assert security.verify_password("correct horse battery staple", hashed)


def test_password_hash_rejects_wrong_password():
    hashed = security.hash_password("correct horse battery staple")

    assert not security.verify_password("wrong password", hashed)


def test_access_token_round_trip_carries_subject_and_role():
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id, "ADMIN")

    payload = security.decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "ADMIN"


def test_refresh_token_round_trip_carries_subject_and_type():
    user_id = uuid.uuid4()
    token = security.create_refresh_token(user_id)

    payload = security.decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"


def test_decode_token_rejects_tampered_signature():
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id, "ADMIN")
    header, payload, signature = token.split(".")
    # Flip the first char of the signature rather than the last: base64url's final group can
    # have unused padding bits, so mutating the very last character is occasionally a no-op on
    # the decoded bytes (flaky). The first character has no such edge case.
    flipped = "A" if signature[0] != "A" else "B"
    tampered = f"{header}.{payload}.{flipped}{signature[1:]}"

    with pytest.raises(jwt.PyJWTError):
        security.decode_token(tampered)


def test_decode_token_rejects_expired_token(monkeypatch):
    from datetime import datetime, timedelta, timezone

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2020, 1, 1, tzinfo=timezone.utc)

    monkeypatch.setattr(security, "datetime", _FrozenDatetime)
    user_id = uuid.uuid4()
    token = security.create_access_token(user_id, "ADMIN")

    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(token)
