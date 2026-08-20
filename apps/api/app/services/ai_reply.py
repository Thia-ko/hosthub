"""AI-generated auto-reply: the last step of `app.api.v1.routers.webhooks._maybe_auto_reply`'s
pipeline, tried after `app.services.queue.try_handoff` and `app.services.chatbot.try_reply` have
both declined the message. Owns the daily token budget gate, provider dispatch (including audio
transcription / image vision), the AI's optional `[ESCALAR]` escalation tag
(`app.services.escalation`), and persisting both the outbound message and an `AiAssistRequest`
audit row."""

import logging
from typing import Sequence

import httpx

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_assist_request import AiAssistRequest, AiAssistStatus
from app.models.attendance_queue import AttendanceQueue
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.conversation_thread import ConversationThread, EscalationReason
from app.models.instance import Instance
from app.services.ai_assist_budget import get_daily_limit, get_usage_today
from app.services.ai_assist_provider import get_ai_assist_provider
from app.services.escalation import split_escalation_tag
from app.services.plans import InstanceFeatures
from app.services.prompt_content import get_current_prompt_content
from app.services.queue import (
    enqueue_thread,
    escalate_for_ai_failure,
    handoff_if_requested,
    resolve_queue_by_slug,
    to_escalation_options,
)
from app.services.whatsapp_channel import ParsedInboundMessage, send_reply

logger = logging.getLogger(__name__)


async def try_reply(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    queues: Sequence[AttendanceQueue],
    features: InstanceFeatures,
) -> bool:
    """Last step: generates and sends an AI reply for a message neither `queue.try_handoff` nor
    `chatbot.try_reply` claimed. Gates on the plan's ai_enabled flag, the daily token budget, and
    a configured provider+prompt; transcribes audio / attaches images; re-checks for a handoff
    request that only becomes visible after transcription; calls the provider; strips and acts
    on its optional `[ESCALAR]` tag; and persists the outbound message plus an AiAssistRequest
    audit row. Returns True if a reply (or a post-transcription handoff) was sent, False if
    skipped by a feature/budget/config gate."""
    if not features.ai_enabled:
        logger.info("Instance %s has AI disabled for its plan; skipping auto-reply", instance.id)
        return False

    used_today = await get_usage_today(db, instance.id)
    if used_today >= get_daily_limit(instance):
        logger.warning("Instance %s hit its daily AI assist budget; skipping auto-reply", instance.id)
        return False

    provider = await get_ai_assist_provider(db)
    if not provider.is_configured:
        logger.warning("AI assist provider not configured; skipping auto-reply for instance %s", instance.id)
        return False

    system_prompt = await get_current_prompt_content(db, instance)
    if not system_prompt:
        logger.warning("Instance %s has no saved prompt; skipping auto-reply", instance.id)
        return False

    # Failures here are external, expected, and must never leave the customer without any
    # reply: httpx.HTTPError covers connection drops, timeouts, and non-2xx responses raised by
    # response.raise_for_status() (rate limit/429, provider outage/5xx); KeyError/ValueError
    # cover a "successful" response whose body doesn't have the shape we expect (missing
    # choices/message, or - for transcribe_bytes - an empty transcript). Anything else (a real
    # bug elsewhere in this function) is intentionally left to propagate to
    # `webhooks._maybe_auto_reply`'s catch-all, which logs it but still doesn't fall back to a
    # human - only genuine provider failures should trigger that.
    image_url: str | None = None
    log_prefix = "[atendimento]"
    message_text = parsed.text
    try:
        if parsed.media_kind == "audio":
            assert parsed.media_url is not None
            message_text = await provider.transcribe(parsed.media_url)
            log_prefix = "[atendimento-audio]"
        elif parsed.media_kind == "image":
            image_url = parsed.media_url
            message_text = parsed.text or "(imagem sem legenda)"
            log_prefix = "[atendimento-imagem]"

        # Re-checked here (in addition to `queue.try_handoff`, which skips audio entirely)
        # because an audio message's handoff request only becomes visible after transcription.
        if parsed.media_kind == "audio" and await handoff_if_requested(
            db, instance, parsed, thread, queues, message_text
        ):
            return True

        reply, prompt_tokens, completion_tokens = await provider.reply(
            system_prompt, [], message_text, image_url=image_url, escalation_queues=to_escalation_options(queues)
        )
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.error(
            "%s AI provider call failed for instance %s (%s): %s",
            log_prefix,
            instance.id,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        await escalate_for_ai_failure(db, instance, parsed, thread, queues)
        return True

    reply, escalate, ai_confidence, queue_slug = split_escalation_tag(reply)

    await send_reply(instance, parsed.sender_number, reply, parsed.whatsbotmais_token)

    db.add(
        ConversationMessage(
            instance_id=instance.id,
            sender_number=parsed.sender_number,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.TEXT,
            text=reply,
            origin=MessageOrigin.AI,
        )
    )

    db.add(
        AiAssistRequest(
            instance_id=instance.id,
            user_id=instance.created_by_admin_id,
            instruction=f"{log_prefix} {message_text}",
            suggested_content=reply,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            status=AiAssistStatus.DISCARDED,
        )
    )
    if escalate:
        thread.ai_paused = True
        thread.escalated = True
        chosen_queue = resolve_queue_by_slug(queues, queue_slug)
        await enqueue_thread(
            db,
            thread,
            escalation_reason=EscalationReason.AI_UNCERTAIN,
            ai_confidence=ai_confidence,
            queue_id=chosen_queue.id,
        )
        logger.info(
            "Instance %s: AI escalated conversation with %s to queue '%s'",
            instance.id,
            parsed.sender_number,
            chosen_queue.slug,
        )
    await db.commit()
    return True
