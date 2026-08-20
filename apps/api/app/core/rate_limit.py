import time
import uuid
from collections import defaultdict, deque

from fastapi import HTTPException, Path, Request, status

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


async def rate_limit_demo_ip(request: Request) -> None:
    """Caps requests por IP aparente para o chat publico da demo, alem do cap de mensagens por
    sessao e do orcamento diario de tokens (app.services.demo_sandbox), ambos no banco."""
    _check(f"demo:{request.client.host if request.client else 'unknown'}")


async def rate_limit_public_stats_ip(request: Request) -> None:
    """Caps requests por IP para o endpoint publico de estatisticas agregadas da plataforma
    (o ticker de prova social da landing) - bucket separado do /demo/chat pra um nao consumir
    o orcamento do outro."""
    _check(f"public-stats:{request.client.host if request.client else 'unknown'}")


def rate_limit_api_key(api_key_id: uuid.UUID) -> None:
    """Caps requests per API key so a single integration can't overwhelm the API. Called
    directly from app.core.api_key_auth.require_scope once the key is resolved (its id isn't
    known until after auth, so this isn't a plain FastAPI Depends like the others above)."""
    _check(f"apikey:{api_key_id}")
