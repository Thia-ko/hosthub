"""Unit tests for the pure parts of the outbound webhooks feature: the fixed event catalog
(app.services.outbound_webhooks), the event-name validation used by the CRUD router, and the
HMAC-SHA256 request signing (app.services.outbound_webhooks.sign_payload)."""

import hashlib
import hmac

import pytest
from fastapi import HTTPException

from app.api.v1.routers.outbound_webhooks import _validate_events
from app.services.outbound_webhooks import EVENTS, MESSAGE_RECEIVED, PROMPT_PENDING, THREAD_ESCALATED, sign_payload


def test_events_catalog_matches_the_named_constants():
    assert set(EVENTS) == {MESSAGE_RECEIVED, THREAD_ESCALATED, PROMPT_PENDING}


def test_validate_events_accepts_known_events():
    _validate_events([MESSAGE_RECEIVED, THREAD_ESCALATED])  # must not raise


def test_validate_events_accepts_empty_list():
    _validate_events([])  # must not raise


def test_validate_events_rejects_unknown_event():
    with pytest.raises(HTTPException) as exc_info:
        _validate_events(["message_received", "bogus_event"])

    assert exc_info.value.status_code == 422
    assert "bogus_event" in exc_info.value.detail


def test_validate_events_rejects_typo_of_a_real_event():
    with pytest.raises(HTTPException):
        _validate_events(["thread_escalate"])


# --- sign_payload --------------------------------------------------------------------------------


def test_sign_payload_matches_manual_hmac_sha256():
    body = b'{"event":"message_received"}'
    secret = "s3cr3t"

    expected = "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    assert sign_payload(secret, body) == expected


def test_sign_payload_differs_for_different_secrets():
    body = b"same body"

    assert sign_payload("secret-a", body) != sign_payload("secret-b", body)


def test_sign_payload_differs_for_different_bodies():
    secret = "same-secret"

    assert sign_payload(secret, b"body-a") != sign_payload(secret, b"body-b")


def test_sign_payload_is_deterministic():
    assert sign_payload("secret", b"body") == sign_payload("secret", b"body")
