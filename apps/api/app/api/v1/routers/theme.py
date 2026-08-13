from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin, require_cf_access_header
from app.db.session import get_db
from app.models.theme_setting import (
    DEFAULT_DARK_PRIMARY,
    DEFAULT_DARK_SECONDARY,
    DEFAULT_LIGHT_PRIMARY,
    DEFAULT_LIGHT_SECONDARY,
    SINGLETON_ID,
    ThemeSetting,
)
from app.models.user import User
from app.schemas.theme import ThemeSettingsOut, ThemeSettingsUpdateRequest

router = APIRouter(prefix="/theme", tags=["theme"])


@router.get("", response_model=ThemeSettingsOut)
async def get_theme(db: AsyncSession = Depends(get_db)) -> ThemeSetting:
    theme = await db.get(ThemeSetting, SINGLETON_ID)
    if theme is not None:
        return theme
    return ThemeSetting(
        light_primary_color=DEFAULT_LIGHT_PRIMARY,
        light_secondary_color=DEFAULT_LIGHT_SECONDARY,
        dark_primary_color=DEFAULT_DARK_PRIMARY,
        dark_secondary_color=DEFAULT_DARK_SECONDARY,
    )


@router.put("", response_model=ThemeSettingsOut, dependencies=[Depends(require_cf_access_header)])
async def update_theme(
    payload: ThemeSettingsUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ThemeSetting:
    theme = await db.get(ThemeSetting, SINGLETON_ID)
    if theme is None:
        theme = ThemeSetting(id=SINGLETON_ID)
        db.add(theme)
    theme.light_primary_color = payload.light_primary_color
    theme.light_secondary_color = payload.light_secondary_color
    theme.dark_primary_color = payload.dark_primary_color
    theme.dark_secondary_color = payload.dark_secondary_color
    theme.updated_by_user_id = admin.id
    await db.commit()
    await db.refresh(theme)
    return theme
