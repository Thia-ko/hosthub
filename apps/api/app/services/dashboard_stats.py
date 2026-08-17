"""Daily aggregation helpers shared by the instance dashboard summary and the admin portfolio
overview - both need the same "last N days" rollup (messages, AI tokens), scoped to one instance
or platform-wide, so the query lives here once instead of being duplicated per router."""

import uuid
from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_assist_request import AiAssistRequest
from app.models.conversation_message import ConversationMessage, MessageDirection


def _range_start(days: int) -> datetime:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start - timedelta(days=days - 1)


async def get_daily_message_counts(
    db: AsyncSession, *, instance_id: uuid.UUID | None = None, days: int = 7
) -> list[tuple[date_type, int]]:
    """Inbound customer-message counts per day for the last `days` days (oldest first, today
    last). Same INBOUND-only filter as the hourly breakdown in dashboard.get_summary - see its
    comment for why (excludes our own echoes/outbound sends)."""
    range_start = _range_start(days)
    day_col = cast(ConversationMessage.created_at, Date)
    query = select(day_col.label("day"), func.count().label("count")).where(
        ConversationMessage.direction == MessageDirection.INBOUND,
        ConversationMessage.created_at >= range_start,
    )
    if instance_id is not None:
        query = query.where(ConversationMessage.instance_id == instance_id)
    query = query.group_by("day")
    counts_by_day = {day: count for day, count in (await db.execute(query)).all()}
    start_date = range_start.date()
    return [(start_date + timedelta(days=i), counts_by_day.get(start_date + timedelta(days=i), 0)) for i in range(days)]


async def get_daily_token_usage(
    db: AsyncSession, *, instance_id: uuid.UUID | None = None, days: int = 7
) -> list[tuple[date_type, int]]:
    """AI assist token usage per day for the last `days` days (oldest first, today last)."""
    range_start = _range_start(days)
    day_col = cast(AiAssistRequest.created_at, Date)
    query = select(day_col.label("day"), func.coalesce(func.sum(AiAssistRequest.total_tokens), 0).label("tokens")).where(
        AiAssistRequest.created_at >= range_start,
    )
    if instance_id is not None:
        query = query.where(AiAssistRequest.instance_id == instance_id)
    query = query.group_by("day")
    tokens_by_day = {day: tokens for day, tokens in (await db.execute(query)).all()}
    start_date = range_start.date()
    return [(start_date + timedelta(days=i), tokens_by_day.get(start_date + timedelta(days=i), 0)) for i in range(days)]
