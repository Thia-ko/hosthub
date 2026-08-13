import uuid

import jwt
from fastapi import Cookie, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ACCESS_COOKIE_NAME, decode_token
from app.db.session import get_db
from app.models.instance import Instance
from app.models.user import User, UserRole


async def get_current_user(
    hh_access: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nao autenticado")
    if not hh_access:
        raise unauthorized
    try:
        payload = decode_token(hh_access)
    except jwt.PyJWTError:
        raise unauthorized
    user_id = payload.get("sub")
    if not user_id:
        raise unauthorized
    user = await db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito ao administrador")
    return user


async def get_owned_instance(
    instance_id: uuid.UUID = Path(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Instance:
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia nao encontrada")
    result = await db.execute(select(Instance).where(Instance.id == instance_id))
    instance = result.scalar_one_or_none()
    if instance is None:
        raise not_found
    if user.role != UserRole.ADMIN and instance.owner_user_id != user.id:
        raise not_found
    return instance
