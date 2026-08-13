from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.instance import Instance
from app.models.prompt_version import PromptVersion
from app.models.webhook_event import WebhookEvent
from app.schemas.dashboard import DashboardSummary, HourlyCount
from app.services.ai_assist_budget import get_daily_limit, get_usage_today

router = APIRouter(prefix="/instances/{instance_id}/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    date: date_type | None = Query(default=None),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    target_date = date or datetime.now(timezone.utc).date()
    range_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    range_end = range_start + timedelta(days=1)

    hourly_result = await db.execute(
        select(extract("hour", WebhookEvent.received_at).label("hour"), func.count().label("count"))
        .where(
            WebhookEvent.instance_id == instance.id,
            WebhookEvent.received_at >= range_start,
            WebhookEvent.received_at < range_end,
        )
        .group_by("hour")
    )
    counts_by_hour = {int(hour): count for hour, count in hourly_result.all()}
    events_by_hour = [HourlyCount(hour=h, count=counts_by_hour.get(h, 0)) for h in range(24)]
    total_events = sum(counts_by_hour.values())

    prompt_versions_count = (
        await db.execute(
            select(func.count()).select_from(PromptVersion).where(PromptVersion.instance_id == instance.id)
        )
    ).scalar_one()

    ai_assist_usage_today = await get_usage_today(db, instance.id)

    return DashboardSummary(
        date=target_date,
        total_events=total_events,
        events_by_hour=events_by_hour,
        prompt_versions_count=prompt_versions_count,
        ai_assist_usage_today=ai_assist_usage_today,
        ai_assist_daily_limit=get_daily_limit(instance),
    )
