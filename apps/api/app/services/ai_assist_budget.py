from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_assist_request import AiAssistRequest
from app.models.instance import Instance


def _utc_midnight_today() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def next_reset_at() -> datetime:
    return _utc_midnight_today() + timedelta(days=1)


async def get_usage_today(db: AsyncSession, instance_id) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(AiAssistRequest.total_tokens), 0)).where(
            AiAssistRequest.instance_id == instance_id,
            AiAssistRequest.created_at >= _utc_midnight_today(),
        )
    )
    return result.scalar_one()


def get_daily_limit(instance: Instance) -> int:
    return instance.ai_assist_daily_token_limit or settings.AI_ASSIST_DAILY_TOKEN_LIMIT_DEFAULT
