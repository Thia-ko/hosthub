from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import require_admin, require_cf_access_header
from app.db.session import get_db
from app.models.ai_settings import SINGLETON_ID, AiSettings
from app.models.user import User
from app.schemas.ai_settings import AiSettingsOut, AiSettingsUpdateRequest
from app.services.ai_settings import api_key_source, get_ai_settings_row

router = APIRouter(prefix="/ai-settings", tags=["ai-settings"])


def _to_out(row: AiSettings | None) -> AiSettingsOut:
    return AiSettingsOut(
        base_url=(row.base_url if row and row.base_url else settings.AI_ASSIST_BASE_URL),
        model=(row.model if row and row.model else settings.AI_ASSIST_MODEL),
        transcribe_model=(row.transcribe_model if row and row.transcribe_model else settings.AI_ASSIST_TRANSCRIBE_MODEL),
        api_key_source=api_key_source(row),
        updated_at=row.updated_at if row else None,
    )


@router.get("", response_model=AiSettingsOut, dependencies=[Depends(require_admin)])
async def get_ai_settings(db: AsyncSession = Depends(get_db)) -> AiSettingsOut:
    return _to_out(await get_ai_settings_row(db))


@router.put("", response_model=AiSettingsOut, dependencies=[Depends(require_cf_access_header)])
async def update_ai_settings(
    payload: AiSettingsUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AiSettingsOut:
    row = await get_ai_settings_row(db)
    if row is None:
        row = AiSettings(id=SINGLETON_ID)
        db.add(row)

    row.base_url = payload.base_url
    row.model = payload.model
    row.transcribe_model = payload.transcribe_model
    if payload.clear_api_key:
        row.api_key = None
    elif payload.api_key:
        row.api_key = payload.api_key
    row.updated_by_user_id = admin.id

    await db.commit()
    await db.refresh(row)
    return _to_out(row)
