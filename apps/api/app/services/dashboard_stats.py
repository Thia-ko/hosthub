"""Daily aggregation helpers shared by the instance dashboard summary and the admin portfolio
overview - both need the same "last N days" rollup (messages, AI tokens), scoped to one instance
or platform-wide, so the query lives here once instead of being duplicated per router."""

import uuid
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_assist_request import AiAssistRequest
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageOrigin
from app.models.conversation_thread import ConversationThread


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


# Documented estimate, not measured: average minutes a human agent would spend manually
# handling one WhatsApp conversation end-to-end (read, think, type, follow up). Used only to
# turn "threads the AI resolved without a human" into a rough "hours saved" figure for the
# dashboard - edit this constant if the real average for your team differs.
AVG_MANUAL_HANDLE_MINUTES = 4


@dataclass(frozen=True)
class ResolutionStats:
    threads_with_activity: int
    ai_resolved_threads: int
    resolution_rate_pct: float | None
    estimated_hours_saved: float


async def get_resolution_stats(
    db: AsyncSession, *, instance_id: uuid.UUID | None = None, days: int = 7
) -> ResolutionStats:
    """Threads (instance_id, sender_number) with an inbound customer message in the last `days`
    days, and how many of them never needed a human: no OUTBOUND message with origin=HUMAN in
    that window, AND the thread isn't currently sitting in ConversationThread.escalated=True
    (awaiting a human who hasn't replied yet). AI/SYSTEM-origin outbound messages don't disqualify
    a thread - a canned CSAT question or the AI's own reply isn't "a human stepping in".
    `estimated_hours_saved` multiplies ai_resolved_threads by AVG_MANUAL_HANDLE_MINUTES - a
    documented estimate, not measured time."""
    range_start = _range_start(days)

    activity_query = select(ConversationMessage.instance_id, ConversationMessage.sender_number).where(
        ConversationMessage.direction == MessageDirection.INBOUND,
        ConversationMessage.created_at >= range_start,
    )
    human_touched_query = select(ConversationMessage.instance_id, ConversationMessage.sender_number).where(
        ConversationMessage.direction == MessageDirection.OUTBOUND,
        ConversationMessage.origin == MessageOrigin.HUMAN,
        ConversationMessage.created_at >= range_start,
    )
    escalated_query = select(ConversationThread.instance_id, ConversationThread.sender_number).where(
        ConversationThread.escalated.is_(True)
    )
    if instance_id is not None:
        activity_query = activity_query.where(ConversationMessage.instance_id == instance_id)
        human_touched_query = human_touched_query.where(ConversationMessage.instance_id == instance_id)
        escalated_query = escalated_query.where(ConversationThread.instance_id == instance_id)

    activity_threads = set((await db.execute(activity_query.distinct())).all())
    human_touched_threads = set((await db.execute(human_touched_query.distinct())).all())
    still_escalated_threads = set((await db.execute(escalated_query.distinct())).all())

    threads_with_activity = len(activity_threads)
    ai_resolved_threads = len(activity_threads - human_touched_threads - still_escalated_threads)
    resolution_rate_pct = (
        round(ai_resolved_threads / threads_with_activity * 100, 1) if threads_with_activity > 0 else None
    )
    estimated_hours_saved = round(ai_resolved_threads * AVG_MANUAL_HANDLE_MINUTES / 60, 1)

    return ResolutionStats(
        threads_with_activity=threads_with_activity,
        ai_resolved_threads=ai_resolved_threads,
        resolution_rate_pct=resolution_rate_pct,
        estimated_hours_saved=estimated_hours_saved,
    )
