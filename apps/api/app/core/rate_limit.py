import time
from collections import defaultdict, deque

from fastapi import HTTPException, Path, status

# Single-process, in-memory limiter: fine for the current one-replica API deployment.
# If the API ever scales to multiple replicas, this needs a shared store (e.g. Redis) instead.
_WINDOW_SECONDS = 60.0
_MAX_REQUESTS_PER_WINDOW = 120  # ~2 req/s sustained, generous burst allowance

_hits: dict[str, deque[float]] = defaultdict(deque)


def _check(key: str) -> None:
    now = time.monotonic()
    bucket = _hits[key]
    while bucket and now - bucket[0] > _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _MAX_REQUESTS_PER_WINDOW:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas requisicoes para este webhook, tente novamente em instantes",
        )
    bucket.append(now)


async def rate_limit_webhook_token(webhook_token: str = Path(...)) -> None:
    """Caps requests per webhook_token so a leaked or misbehaving token can't flood the API."""
    _check(f"webhook:{webhook_token}")
