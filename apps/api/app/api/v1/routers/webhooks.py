import logging
from typing import Sequence

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_instance_by_webhook_token
from app.core.rate_limit import rate_limit_webhook_token
from app.db.session import get_db
from app.models.attendance_queue import AttendanceQueue
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance, InstanceStatus, WhatsAppProvider
from app.models.webhook_event import WebhookEvent
from app.schemas.instance_prompt import InstancePromptOut
from app.services import ai_reply, csat
from app.services.chatbot import try_reply as try_chatbot_reply
from app.services.conversation_analyzer import maybe_trigger_analysis
from app.services.conversation_threads import get_or_create_thread
from app.services.outbound_webhooks import MESSAGE_RECEIVED, THREAD_ESCALATED, dispatch_event
from app.services.plans import get_features
from app.services.prompt_content import get_current_prompt_version
from app.services.queue import reopen_if_resolved, try_handoff
from app.services.whatsapp_channel import (
    ParsedInboundMessage,
    WhatsAppChannelError,
    parse_inbound_message,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_EXCLUDED_HEADERS = {"cookie", "authorization", "host", "connection", "content-length"}

_MESSAGE_KIND_BY_MEDIA_KIND = {None: MessageKind.TEXT, "audio": MessageKind.AUDIO, "image": MessageKind.IMAGE}


async def _load_queues(db: AsyncSession, instance_id) -> list[AttendanceQueue]:
    """All of an instance's configured queues (active and inactive), position-ordered - loaded
    once per webhook call and threaded through routing/reopen/AI-reply so the request doesn't
    re-query it per escalation trigger."""
    result = await db.execute(
        select(AttendanceQueue).where(AttendanceQueue.instance_id == instance_id).order_by(AttendanceQueue.position)
    )
    return list(result.scalars().all())


def _channel_is_ready(instance: Instance, parsed: ParsedInboundMessage) -> bool:
    """Whether there's a WhatsApp channel to actually send a reply on. WhatsBotMais never sets
    `whatsapp_instance_name` (no per-instance credential - the reply token rides on every
    inbound message, see `parsed.whatsbotmais_token`); only Evolution connections use that
    field. Gating on `whatsapp_instance_name` alone would silently drop every auto-reply for a
    WhatsBotMais-only instance even with a valid prompt configured."""
    if instance.status != InstanceStatus.ACTIVE:
        return False
    if instance.whatsapp_provider == WhatsAppProvider.META_CLOUD and instance.meta_phone_number_id and instance.meta_access_token:
        return True
    return bool(instance.whatsapp_instance_name or parsed.whatsbotmais_token)


async def _maybe_auto_reply(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    queues: Sequence[AttendanceQueue],
) -> None:
    """Best-effort: generates and sends a WhatsApp reply for an inbound customer message.
    Never raises - failures are logged so the webhook call always succeeds for the sender.
    Delegates, in priority order, to `app.services.queue.try_handoff` (explicit human
    request), `app.services.chatbot.try_reply` (deterministic tree) and
    `app.services.ai_reply.try_reply` (AI provider) - the first one that claims the message
    stops the chain. Everything below this router's own HTTP concerns (parsing, persistence,
    channel readiness) now lives in the dedicated service each step belongs to."""
    if not _channel_is_ready(instance, parsed):
        return
    if thread.ai_paused:
        return

    try:
        if await try_handoff(db, instance, parsed, thread, queues):
            return

        features = get_features(instance)

        if await try_chatbot_reply(db, instance, parsed, thread, features):
            return

        await ai_reply.try_reply(db, instance, parsed, thread, queues, features)
    except WhatsAppChannelError:
        logger.exception("Failed to send WhatsApp reply for instance %s", instance.id)
    except Exception:  # noqa: BLE001 - webhook must never fail because of the reply pipeline
        logger.exception("Unexpected error generating auto-reply for instance %s", instance.id)


@router.post("/{webhook_token}", dependencies=[Depends(rate_limit_webhook_token)])
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    instance: Instance = Depends(get_instance_by_webhook_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_body = await request.body()
    try:
        payload = await request.json() if raw_body else {}
    except ValueError:
        payload = {"_raw": raw_body.decode("utf-8", errors="replace")}

    headers = {key: value for key, value in request.headers.items() if key.lower() not in _EXCLUDED_HEADERS}

    db.add(WebhookEvent(instance_id=instance.id, headers_json=headers, payload_json=payload))

    parsed = parse_inbound_message(payload) if isinstance(payload, dict) else None
    thread: ConversationThread | None = None
    queues: list[AttendanceQueue] = []
    if parsed is not None:
        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number=parsed.sender_number,
                direction=MessageDirection.INBOUND,
                kind=_MESSAGE_KIND_BY_MEDIA_KIND[parsed.media_kind],
                text=parsed.text,
                media_url=parsed.media_url,
            )
        )
        thread = await get_or_create_thread(db, instance.id, parsed.sender_number)
        if parsed.whatsbotmais_token:
            thread.last_whatsbotmais_token = parsed.whatsbotmais_token
        queues = await _load_queues(db, instance.id)
        await reopen_if_resolved(db, thread, queues)
    await db.commit()

    if parsed is not None and thread is not None:
        background_tasks.add_task(
            dispatch_event,
            instance.id,
            MESSAGE_RECEIVED,
            {"sender_number": parsed.sender_number, "text": parsed.text, "media_kind": parsed.media_kind},
        )
        csat_handled = await csat.try_capture(db, instance, parsed)
        if not csat_handled:
            was_escalated = thread.escalated
            await _maybe_auto_reply(db, instance, parsed, thread, queues)
            if thread.escalated and not was_escalated:
                background_tasks.add_task(
                    dispatch_event, instance.id, THREAD_ESCALATED, {"sender_number": parsed.sender_number}
                )
        # Fire-and-forget: re-analyzes the thread (extracts business data/FAQs/patterns and,
        # if configured, auto-generates a pending prompt) once enough new messages piled up.
        background_tasks.add_task(maybe_trigger_analysis, instance.id, parsed.sender_number)

    return {"received": True}


@router.get("/{webhook_token}", dependencies=[Depends(rate_limit_webhook_token)])
async def verify_webhook(
    webhook_token: str,
    request: Request,
    instance: Instance = Depends(get_instance_by_webhook_token),
) -> Response:
    """Meta WhatsApp Cloud API's webhook verification handshake: Meta issues a GET with these
    query params (to the same URL used for inbound POSTs) when a webhook is first registered
    (or re-verified) in the Meta App dashboard, and expects the raw challenge echoed back."""
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and verify_token == instance.webhook_token and challenge is not None:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Falha na verificacao do webhook")


@router.get(
    "/{webhook_token}/prompt",
    response_model=InstancePromptOut,
    dependencies=[Depends(rate_limit_webhook_token)],
)
async def get_active_prompt(
    instance: Instance = Depends(get_instance_by_webhook_token),
    db: AsyncSession = Depends(get_db),
) -> InstancePromptOut:
    version = await get_current_prompt_version(db, instance)
    return InstancePromptOut(
        instance_id=instance.id,
        name=instance.name,
        status=instance.status,
        prompt=version.content if version else "",
        version_number=version.version_number if version else None,
    )
