"""Unit tests for app.services.api_keys (key generation/hashing) and the scope validation used
by the api_keys CRUD router (app.api.v1.routers.api_keys._validate_scopes) - same convention as
test_outbound_webhooks.py for the sibling outbound-webhooks feature."""

import pytest
from fastapi import HTTPException

from app.api.v1.routers.api_keys import _validate_scopes
from app.services.api_keys import DATA_READ, KEY_PREFIX, MESSAGES_WRITE, PROMPT_READ, SCOPES, generate_api_key, hash_api_key


def test_scopes_catalog_matches_the_named_constants():
    assert set(SCOPES) == {PROMPT_READ, DATA_READ, MESSAGES_WRITE}


def test_generate_api_key_raw_key_starts_with_prefix():
    raw_key, _, _ = generate_api_key()

    assert raw_key.startswith(KEY_PREFIX)


def test_generate_api_key_hash_matches_hashing_the_raw_key_again():
    raw_key, _, key_hash = generate_api_key()

    assert hash_api_key(raw_key) == key_hash


def test_generate_api_key_prefix_is_a_prefix_of_the_raw_key():
    raw_key, prefix, _ = generate_api_key()

    assert raw_key.startswith(prefix)
    assert len(prefix) < len(raw_key)


def test_generate_api_key_is_unique_per_call():
    raw_a, _, hash_a = generate_api_key()
    raw_b, _, hash_b = generate_api_key()

    assert raw_a != raw_b
    assert hash_a != hash_b


def test_hash_api_key_is_deterministic():
    assert hash_api_key("hhk_same-token") == hash_api_key("hhk_same-token")


def test_hash_api_key_differs_for_different_tokens():
    assert hash_api_key("hhk_token-a") != hash_api_key("hhk_token-b")


def test_validate_scopes_accepts_known_scopes():
    _validate_scopes([PROMPT_READ, MESSAGES_WRITE])  # must not raise


def test_validate_scopes_rejects_empty_list():
    with pytest.raises(HTTPException) as exc_info:
        _validate_scopes([])

    assert exc_info.value.status_code == 422


def test_validate_scopes_rejects_unknown_scope():
    with pytest.raises(HTTPException) as exc_info:
        _validate_scopes([PROMPT_READ, "bogus:scope"])

    assert exc_info.value.status_code == 422
    assert "bogus:scope" in exc_info.value.detail
