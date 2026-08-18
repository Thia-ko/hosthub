"""Integration tests for the demo sandbox budget guards (app.services.demo_sandbox)."""

import uuid

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.db.session import async_session
from app.services import demo_sandbox


async def _record(session_id: str, total_tokens: int = 10) -> None:
    async with async_session() as db:
        prompt_tokens = total_tokens // 2
        completion_tokens = total_tokens - prompt_tokens
        await demo_sandbox.record_usage(db, session_id, prompt_tokens, completion_tokens)


async def test_session_budget_blocks_after_max_messages():
    session_id = f"sess-{uuid.uuid4()}"
    for _ in range(demo_sandbox.MAX_MESSAGES_PER_SESSION):
        await _record(session_id)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await demo_sandbox.check_session_budget(db, session_id)
        assert exc_info.value.status_code == 429


async def test_session_budget_leaves_other_sessions_unaffected():
    exhausted_session = f"sess-{uuid.uuid4()}"
    fresh_session = f"sess-{uuid.uuid4()}"
    for _ in range(demo_sandbox.MAX_MESSAGES_PER_SESSION):
        await _record(exhausted_session)

    async with async_session() as db:
        # Does not raise.
        await demo_sandbox.check_session_budget(db, fresh_session)


async def test_daily_budget_blocks_once_limit_reached(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_DAILY_TOKEN_LIMIT", 100)
    session_id = f"sess-{uuid.uuid4()}"
    await _record(session_id, total_tokens=60)
    await _record(session_id, total_tokens=60)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await demo_sandbox.check_daily_budget(db)
        assert exc_info.value.status_code == 429


async def test_daily_budget_allows_usage_below_limit(monkeypatch):
    monkeypatch.setattr(settings, "DEMO_DAILY_TOKEN_LIMIT", 1_000_000)
    session_id = f"sess-{uuid.uuid4()}"
    await _record(session_id, total_tokens=10)

    async with async_session() as db:
        # Does not raise.
        await demo_sandbox.check_daily_budget(db)
