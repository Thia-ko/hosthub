import logging
import uuid

import httpx
from sqlalchemy import select

from app.db.session import async_session
from app.models.outbound_webhook_subscription import OutboundWebhookSubscription
from app.utils.json_utils import safe_parse_json_array

logger = logging.getLogger(__name__)

# Fixed set of events an instance can subscribe to. Kept small and named after the business
# moment they represent, not the internal trigger, so the contract stays stable if the
# implementation detail behind each one changes.
MESSAGE_RECEIVED = "message_received"
THREAD_ESCALATED = "thread_escalated"
PROMPT_PENDING = "prompt_pending"

EVENTS = (MESSAGE_RECEIVED, THREAD_ESCALATED, PROMPT_PENDING)

_TIMEOUT_SECONDS = 10


async def dispatch_event(instance_id: uuid.UUID, event: str, payload: dict) -> None:
    """Fire-and-forget: POSTs `payload` to every active subscription for `instance_id` that
    listens to `event`. Best-effort, single attempt, no retry/backoff - never raises, one
    subscriber's outage never affects another or the caller."""
    async with async_session() as db:
        result = await db.execute(
            select(OutboundWebhookSubscription).where(
                OutboundWebhookSubscription.instance_id == instance_id,
                OutboundWebhookSubscription.active.is_(True),
            )
        )
        subscriptions = [
            sub for sub in result.scalars().all() if event in safe_parse_json_array(sub.events)
        ]

    if not subscriptions:
        return

    body = {"event": event, "instance_id": str(instance_id), **payload}
    async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
        for sub in subscriptions:
            try:
                response = await client.post(sub.url, json=body)
                response.raise_for_status()
            except httpx.HTTPError:
                logger.exception(
                    "Outbound webhook delivery failed: instance=%s event=%s url=%s", instance_id, event, sub.url
                )
