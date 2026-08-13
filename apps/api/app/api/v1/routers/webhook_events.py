from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.instance import Instance
from app.models.webhook_event import WebhookEvent
from app.schemas.webhook_event import WebhookEventOut

router = APIRouter(prefix="/instances/{instance_id}/webhook-events", tags=["webhook-events"])


@router.get("", response_model=list[WebhookEventOut])
async def list_webhook_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> list[WebhookEvent]:
    result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.instance_id == instance.id)
        .order_by(WebhookEvent.received_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
