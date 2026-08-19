import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_owned_instance
from app.db.session import get_db
from app.models.api_key import ApiKey
from app.models.instance import Instance
from app.models.user import User
from app.schemas.api_key import ApiKeyCreatedOut, ApiKeyCreateRequest, ApiKeyOut
from app.services.api_keys import SCOPES, generate_api_key
from app.services.plans import get_features
from app.utils.json_utils import safe_parse_json_array

router = APIRouter(prefix="/instances/{instance_id}/api-keys", tags=["api-keys"])


def _out(key: ApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=key.id,
        name=key.name,
        key_prefix=key.key_prefix,
        scopes=safe_parse_json_array(key.scopes),
        active=key.active,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
    )


def _validate_scopes(scopes: list[str]) -> None:
    if not scopes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Selecione ao menos uma permissao"
        )
    unknown = set(scopes) - set(SCOPES)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Permissoes desconhecidas: {', '.join(sorted(unknown))}",
        )


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[ApiKeyOut]:
    result = await db.execute(
        select(ApiKey).where(ApiKey.instance_id == instance.id).order_by(ApiKey.created_at.desc())
    )
    return [_out(key) for key in result.scalars().all()]


@router.post("", response_model=ApiKeyCreatedOut)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedOut:
    if not get_features(instance).api_access_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="O plano desta instancia nao inclui acesso a API"
        )
    _validate_scopes(payload.scopes)
    raw_key, prefix, key_hash = generate_api_key()
    key = ApiKey(
        instance_id=instance.id,
        name=payload.name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=json.dumps(payload.scopes),
        created_by_user_id=user.id,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return ApiKeyCreatedOut(**_out(key).model_dump(), key=raw_key)


@router.delete("/{key_id}", response_model=dict)
async def revoke_api_key(
    key_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.instance_id == instance.id))
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key nao encontrada")
    key.active = False
    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"revoked": True}
