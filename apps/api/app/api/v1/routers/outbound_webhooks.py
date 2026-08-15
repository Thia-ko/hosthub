import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.instance import Instance
from app.models.outbound_webhook_subscription import OutboundWebhookSubscription
from app.schemas.outbound_webhook import (
    OutboundWebhookSubscriptionCreateRequest,
    OutboundWebhookSubscriptionOut,
    OutboundWebhookSubscriptionUpdateRequest,
)
from app.services.outbound_webhooks import EVENTS
from app.utils.json_utils import safe_parse_json_array

router = APIRouter(prefix="/instances/{instance_id}/outbound-webhooks", tags=["outbound-webhooks"])


def _out(sub: OutboundWebhookSubscription) -> OutboundWebhookSubscriptionOut:
    return OutboundWebhookSubscriptionOut(
        id=sub.id,
        url=sub.url,
        events=safe_parse_json_array(sub.events),
        active=sub.active,
        created_at=sub.created_at,
    )


def _validate_events(events: list[str]) -> None:
    unknown = set(events) - set(EVENTS)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Eventos desconhecidos: {', '.join(sorted(unknown))}. Validos: {', '.join(EVENTS)}",
        )


@router.get("", response_model=list[OutboundWebhookSubscriptionOut])
async def list_subscriptions(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[OutboundWebhookSubscriptionOut]:
    result = await db.execute(
        select(OutboundWebhookSubscription)
        .where(OutboundWebhookSubscription.instance_id == instance.id)
        .order_by(OutboundWebhookSubscription.created_at)
    )
    return [_out(sub) for sub in result.scalars().all()]


@router.post("", response_model=OutboundWebhookSubscriptionOut)
async def create_subscription(
    payload: OutboundWebhookSubscriptionCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> OutboundWebhookSubscriptionOut:
    _validate_events(payload.events)
    sub = OutboundWebhookSubscription(
        instance_id=instance.id, url=payload.url, events=json.dumps(payload.events)
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return _out(sub)


async def _get_subscription(db: AsyncSession, instance: Instance, sub_id: uuid.UUID) -> OutboundWebhookSubscription:
    result = await db.execute(
        select(OutboundWebhookSubscription).where(
            OutboundWebhookSubscription.id == sub_id, OutboundWebhookSubscription.instance_id == instance.id
        )
    )
    sub = result.scalar_one_or_none()
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integracao nao encontrada")
    return sub


@router.put("/{sub_id}", response_model=OutboundWebhookSubscriptionOut)
async def update_subscription(
    sub_id: uuid.UUID,
    payload: OutboundWebhookSubscriptionUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> OutboundWebhookSubscriptionOut:
    sub = await _get_subscription(db, instance, sub_id)
    if payload.url is not None:
        sub.url = payload.url
    if payload.events is not None:
        _validate_events(payload.events)
        sub.events = json.dumps(payload.events)
    if payload.active is not None:
        sub.active = payload.active
    await db.commit()
    await db.refresh(sub)
    return _out(sub)


@router.delete("/{sub_id}", response_model=dict)
async def delete_subscription(
    sub_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    sub = await _get_subscription(db, instance, sub_id)
    await db.delete(sub)
    await db.commit()
    return {"deleted": True}
