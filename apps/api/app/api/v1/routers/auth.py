import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    REFRESH_COOKIE_PATH,
    REFRESH_TOKEN_TTL,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user: User) -> None:
    access_token = create_access_token(user.id, user.role.value)
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    refresh_token = create_refresh_token(user.id)
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
    )


@router.post("/login", response_model=UserOut)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> User:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais invalidas")
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise invalid
    _set_auth_cookies(response, user)
    return user


@router.post("/refresh", response_model=UserOut)
async def refresh(
    response: Response,
    hh_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    invalid = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessao expirada")
    if not hh_refresh:
        raise invalid
    try:
        decoded = decode_token(hh_refresh)
    except Exception:
        raise invalid
    if decoded.get("type") != "refresh":
        raise invalid
    user = await db.get(User, uuid.UUID(decoded["sub"]))
    if user is None or not user.is_active:
        raise invalid
    _set_auth_cookies(response, user)
    return user


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)
    return {"logged_out": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user
