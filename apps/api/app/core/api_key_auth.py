from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import rate_limit_api_key
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.instance import Instance, InstanceStatus
from app.services.api_keys import hash_api_key
from app.services.plans import get_features
from app.utils.json_utils import safe_parse_json_array

_UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key ausente ou invalida")


async def _authenticate(authorization: str | None, db: AsyncSession) -> ApiKey:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise _UNAUTHORIZED
    raw_key = authorization[len("bearer "):].strip()
    if not raw_key:
        raise _UNAUTHORIZED
    result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key)))
    api_key = result.scalar_one_or_none()
    if api_key is None or not api_key.active:
        raise _UNAUTHORIZED
    return api_key


def require_scope(scope: str):
    """FastAPI dependency factory for app.api.v1.routers.external: authenticates the Bearer API
    key, rate-limits per key, requires it to carry `scope`, and resolves the Instance it belongs
    to. Mirrors the shape of app.core.deps.get_owned_instance but for machine callers instead of
    a logged-in user session - no cookie involved."""

    async def _dependency(
        authorization: str | None = Header(default=None),
        db: AsyncSession = Depends(get_db),
    ) -> Instance:
        api_key = await _authenticate(authorization, db)
        rate_limit_api_key(api_key.id)
        if scope not in safe_parse_json_array(api_key.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Esta API key nao tem a permissao '{scope}'"
            )
        instance = await db.get(Instance, api_key.instance_id)
        if instance is None or instance.status != InstanceStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia nao encontrada ou inativa")
        if not get_features(instance).api_access_enabled:
            # Plan-level gate, independent of the key's own scopes: a downgraded instance's
            # existing keys stop working immediately, not just new key creation.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="O plano desta instancia nao inclui acesso a API"
            )
        api_key.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        return instance

    return _dependency
