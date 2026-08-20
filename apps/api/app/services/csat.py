import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance
from app.models.satisfaction_response import SatisfactionResponse
from app.services.whatsapp_channel import ParsedInboundMessage, WhatsAppChannelError, send_reply

logger = logging.getLogger(__name__)

# How long a thread must sit quiet after OUR last reply before we consider the conversation
# "over" and worth asking about. Deliberately a fixed constant, not per-instance config - this
# is a v1 heuristic (HostHub has no explicit "close ticket" concept; WhatsBotMais's own
# auto-close is documented as unreliable, see docs/integrations/whatsbotmais.md).
INACTIVITY_THRESHOLD = timedelta(hours=4)

CSAT_QUESTION = "Antes de encerrar: de 1 a 5, o quanto voce ficou satisfeito com o atendimento? Responda so com o numero."
CSAT_THANKS_MESSAGE = "Muito obrigado pelo feedback!"

_RATING_RE = re.compile(r"[1-5]")


def parse_rating(text: str) -> int | None:
    """Extracts a 1-5 rating from free text (e.g. "5", "nota 4", "3 estrelas"). Returns the
    first digit 1-5 found, or None if there isn't one - deliberately lenient (a customer
    replying "5 estrelas!! otimo" still counts)."""
    match = _RATING_RE.search(text)
    return int(match.group()) if match else None


# --- Inbound: capturing the customer's rating -------------------------------------------------


async def try_capture(db: AsyncSession, instance: Instance, parsed: ParsedInboundMessage) -> bool:
    """Checked first in `app.api.v1.routers.webhooks.receive_webhook`, before the auto-reply
    pipeline (`app.services.queue.try_handoff` / `app.services.chatbot.try_reply` /
    `app.services.ai_reply.try_reply`): if this thread has an unanswered CSAT request pending
    (see `maybe_request_feedback` below) and the message contains a 1-5 rating, records it and
    thanks the customer. Returns True when it handled the message (the caller should skip the
    normal auto-reply flow for it)."""
    pending = await db.scalar(
        select(SatisfactionResponse)
        .where(
            SatisfactionResponse.instance_id == instance.id,
            SatisfactionResponse.sender_number == parsed.sender_number,
            SatisfactionResponse.rating.is_(None),
        )
        .order_by(SatisfactionResponse.requested_at.desc())
        .limit(1)
    )
    if pending is None:
        return False
    rating = parse_rating(parsed.text)
    if rating is None:
        return False

    pending.rating = rating
    pending.response_text = parsed.text
    pending.responded_at = datetime.now(timezone.utc)
    await db.commit()

    try:
        await send_reply(instance, parsed.sender_number, CSAT_THANKS_MESSAGE, parsed.whatsbotmais_token)
        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number=parsed.sender_number,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT,
                text=CSAT_THANKS_MESSAGE,
                origin=MessageOrigin.SYSTEM,
            )
        )
        await db.commit()
    except WhatsAppChannelError:
        logger.exception("Failed to send CSAT thanks message for instance %s", instance.id)
    return True


# --- Outbound: proactively asking --------------------------------------------------------------


async def maybe_request_feedback() -> None:
    """Scheduler-invoked (see app.services.scheduler): for every thread whose most recent
    message is ours and has been sitting unanswered for INACTIVITY_THRESHOLD, sends the CSAT
    question once and records a pending SatisfactionResponse. Never raises - one thread's
    failure (unreachable channel, etc.) never blocks the rest."""
    async with async_session() as db:
        thread_ids = (await db.scalars(select(ConversationThread.id))).all()

    cutoff = datetime.now(timezone.utc) - INACTIVITY_THRESHOLD
    for thread_id in thread_ids:
        try:
            await _maybe_request_feedback_for_thread(thread_id, cutoff)
        except Exception:  # noqa: BLE001 - best-effort background pipeline, must never crash the loop
            logger.exception("CSAT check failed for thread %s", thread_id)


async def _maybe_request_feedback_for_thread(thread_id, cutoff: datetime) -> None:
    async with async_session() as db:
        thread = await db.get(ConversationThread, thread_id)
        if thread is None:
            return

        latest = await db.scalar(
            select(ConversationMessage)
            .where(
                ConversationMessage.instance_id == thread.instance_id,
                ConversationMessage.sender_number == thread.sender_number,
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )
        if latest is None or latest.direction != MessageDirection.OUTBOUND or latest.created_at > cutoff:
            return
        if thread.csat_requested_at is not None and thread.csat_requested_at >= latest.created_at:
            return  # already asked since this reply; awaiting the customer or they won't answer

        instance = await db.get(Instance, thread.instance_id)
        if instance is None or not instance.whatsapp_instance_name:
            return

        try:
            await send_reply(instance, thread.sender_number, CSAT_QUESTION, thread.last_whatsbotmais_token)
        except WhatsAppChannelError:
            logger.exception("Failed to send CSAT question for instance %s / %s", instance.id, thread.sender_number)
            return

        db.add(
            ConversationMessage(
                instance_id=thread.instance_id,
                sender_number=thread.sender_number,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT,
                text=CSAT_QUESTION,
                origin=MessageOrigin.SYSTEM,
            )
        )
        db.add(SatisfactionResponse(instance_id=thread.instance_id, sender_number=thread.sender_number))
        thread.csat_requested_at = datetime.now(timezone.utc)
        await db.commit()
