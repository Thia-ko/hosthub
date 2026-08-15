"""Unit tests for the pure parts of the outbound webhooks feature: the fixed event catalog
(app.services.outbound_webhooks) and the event-name validation used by the CRUD router."""

import pytest
from fastapi import HTTPException

from app.api.v1.routers.outbound_webhooks import _validate_events
from app.services.outbound_webhooks import EVENTS, MESSAGE_RECEIVED, PROMPT_PENDING, THREAD_ESCALATED


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
