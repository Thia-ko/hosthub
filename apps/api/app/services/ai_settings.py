from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_settings import SINGLETON_ID, AiSettings

ApiKeySource = Literal["database", "env", "none"]


@dataclass
class EffectiveAiSettings:
    """AI assist provider config actually used to talk to the model, after merging the
    admin-configured DB row (app.models.ai_settings.AiSettings) over the AI_ASSIST_* env vars.
    A blank/unset DB field falls back to its env counterpart, field by field."""

    api_key: str
    base_url: str
    model: str
    transcribe_model: str


async def get_ai_settings_row(db: AsyncSession) -> AiSettings | None:
    return await db.get(AiSettings, SINGLETON_ID)


def merge_effective_ai_settings(row: AiSettings | None) -> EffectiveAiSettings:
    """Pure merge logic, split out from get_effective_ai_settings so it's testable without a DB."""
    return EffectiveAiSettings(
        api_key=(row.api_key if row and row.api_key else settings.AI_ASSIST_API_KEY) or "",
        base_url=(row.base_url if row and row.base_url else settings.AI_ASSIST_BASE_URL) or settings.AI_ASSIST_BASE_URL,
        model=(row.model if row and row.model else settings.AI_ASSIST_MODEL) or settings.AI_ASSIST_MODEL,
        transcribe_model=(row.transcribe_model if row and row.transcribe_model else settings.AI_ASSIST_TRANSCRIBE_MODEL)
        or settings.AI_ASSIST_TRANSCRIBE_MODEL,
    )


async def get_effective_ai_settings(db: AsyncSession) -> EffectiveAiSettings:
    return merge_effective_ai_settings(await get_ai_settings_row(db))


def api_key_source(row: AiSettings | None) -> ApiKeySource:
    if row and row.api_key:
        return "database"
    if settings.AI_ASSIST_API_KEY:
        return "env"
    return "none"
