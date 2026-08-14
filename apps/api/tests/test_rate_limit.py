"""Unit tests for the in-memory per-token webhook rate limiter (app.core.rate_limit)."""

import pytest
from fastapi import HTTPException

from app.core import rate_limit


@pytest.fixture(autouse=True)
def _reset_hits():
    rate_limit._hits.clear()
    yield
    rate_limit._hits.clear()


async def test_allows_requests_under_the_limit():
    for _ in range(rate_limit._MAX_REQUESTS_PER_WINDOW):
        await rate_limit.rate_limit_webhook_token(webhook_token="tok-a")


async def test_blocks_requests_over_the_limit():
    for _ in range(rate_limit._MAX_REQUESTS_PER_WINDOW):
        await rate_limit.rate_limit_webhook_token(webhook_token="tok-b")

    with pytest.raises(HTTPException) as exc_info:
        await rate_limit.rate_limit_webhook_token(webhook_token="tok-b")

    assert exc_info.value.status_code == 429


async def test_tokens_are_rate_limited_independently():
    for _ in range(rate_limit._MAX_REQUESTS_PER_WINDOW):
        await rate_limit.rate_limit_webhook_token(webhook_token="tok-c")

    # A different token still has its own untouched budget.
    await rate_limit.rate_limit_webhook_token(webhook_token="tok-d")


async def test_old_hits_fall_outside_the_window(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now[0])

    for _ in range(rate_limit._MAX_REQUESTS_PER_WINDOW):
        await rate_limit.rate_limit_webhook_token(webhook_token="tok-e")

    # Advance past the window: the old hits should be evicted, freeing up budget again.
    now[0] += rate_limit._WINDOW_SECONDS + 1
    await rate_limit.rate_limit_webhook_token(webhook_token="tok-e")
