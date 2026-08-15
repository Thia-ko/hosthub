from datetime import date as date_type
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance, require_admin
from app.db.session import get_db
from app.models.ai_assist_request import AiAssistRequest
from app.models.conversation_message import ConversationMessage, MessageDirection
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance, InstanceStatus
from app.models.prompt_version import PromptVersion
from app.models.satisfaction_response import SatisfactionResponse
from app.schemas.dashboard import AdminDashboardOverview, DashboardSummary, HourlyCount
from app.services.ai_assist_budget import get_daily_limit, get_usage_today

router = APIRouter(prefix="/instances/{instance_id}/dashboard", tags=["dashboard"])
admin_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@admin_router.get("/overview", response_model=AdminDashboardOverview, dependencies=[Depends(require_admin)])
async def get_admin_overview(db: AsyncSession = Depends(get_db)) -> AdminDashboardOverview:
    """Cross-instance snapshot for the platform owner: portfolio health at a glance instead of
    clicking into every instance individually."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    counts_by_status = dict(
        (
            await db.execute(
                select(Instance.status, func.count()).group_by(Instance.status)
            )
        ).all()
    )

    pending_prompts = (
        await db.execute(select(func.count()).select_from(PromptVersion).where(PromptVersion.is_pending.is_(True)))
    ).scalar_one()

    escalated_threads = (
        await db.execute(
            select(func.count()).select_from(ConversationThread).where(ConversationThread.escalated.is_(True))
        )
    ).scalar_one()

    messages_today = (
        await db.execute(
            select(func.count()).select_from(ConversationMessage).where(
                ConversationMessage.direction == MessageDirection.INBOUND,
                ConversationMessage.created_at >= today_start,
            )
        )
    ).scalar_one()

    ai_tokens_used_today = (
        await db.execute(
            select(func.coalesce(func.sum(AiAssistRequest.total_tokens), 0)).where(
                AiAssistRequest.created_at >= today_start
            )
        )
    ).scalar_one()

    return AdminDashboardOverview(
        total_instances=sum(counts_by_status.values()),
        active_instances=counts_by_status.get(InstanceStatus.ACTIVE, 0),
        paused_instances=counts_by_status.get(InstanceStatus.PAUSED, 0),
        archived_instances=counts_by_status.get(InstanceStatus.ARCHIVED, 0),
        pending_prompts=pending_prompts,
        escalated_threads=escalated_threads,
        messages_today=messages_today,
        ai_tokens_used_today=ai_tokens_used_today,
    )


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    date: date_type | None = Query(default=None),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    target_date = date or datetime.now(timezone.utc).date()
    range_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    range_end = range_start + timedelta(days=1)

    # Real customer messages only (inbound conversation history) - not raw webhook posts, which
    # also include echoes of our own sends, status updates, and unsupported media we never log
    # as a conversation message.
    hourly_result = await db.execute(
        select(extract("hour", ConversationMessage.created_at).label("hour"), func.count().label("count"))
        .where(
            ConversationMessage.instance_id == instance.id,
            ConversationMessage.direction == MessageDirection.INBOUND,
            ConversationMessage.created_at >= range_start,
            ConversationMessage.created_at < range_end,
        )
        .group_by("hour")
    )
    counts_by_hour = {int(hour): count for hour, count in hourly_result.all()}
    messages_by_hour = [HourlyCount(hour=h, count=counts_by_hour.get(h, 0)) for h in range(24)]
    total_messages = sum(counts_by_hour.values())

    prompt_versions_count = (
        await db.execute(
            select(func.count()).select_from(PromptVersion).where(PromptVersion.instance_id == instance.id)
        )
    ).scalar_one()

    ai_assist_usage_today = await get_usage_today(db, instance.id)

    csat_average, csat_response_count = (
        await db.execute(
            select(func.avg(SatisfactionResponse.rating), func.count(SatisfactionResponse.rating)).where(
                SatisfactionResponse.instance_id == instance.id, SatisfactionResponse.rating.is_not(None)
            )
        )
    ).one()

    return DashboardSummary(
        date=target_date,
        total_messages=total_messages,
        messages_by_hour=messages_by_hour,
        prompt_versions_count=prompt_versions_count,
        ai_assist_usage_today=ai_assist_usage_today,
        ai_assist_daily_limit=get_daily_limit(instance),
        csat_average=round(float(csat_average), 2) if csat_average is not None else None,
        csat_response_count=csat_response_count,
    )
