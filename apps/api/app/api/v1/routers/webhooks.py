import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_instance_by_webhook_token
from app.core.rate_limit import rate_limit_webhook_token
from app.db.session import get_db
from app.models.ai_assist_request import AiAssistRequest, AiAssistStatus
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance, InstanceStatus
from app.models.prompt_version import PromptVersion
from app.models.webhook_event import WebhookEvent
from app.schemas.instance_prompt import InstancePromptOut
from app.services.ai_assist_budget import get_daily_limit, get_usage_today
from app.services.ai_assist_provider import get_ai_assist_provider
from app.services.conversation_analyzer import maybe_trigger_analysis
from app.services.conversation_threads import get_or_create_thread
from app.services.escalation import customer_requests_handoff, split_escalation_tag
from app.services.outbound_webhooks import MESSAGE_RECEIVED, THREAD_ESCALATED, dispatch_event
from app.services.prompt_content import get_current_prompt_content
from app.services.whatsapp_channel import (
    ParsedInboundMessage,
    WhatsAppChannelError,
    parse_inbound_message,
    send_reply,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_EXCLUDED_HEADERS = {"cookie", "authorization", "host", "connection", "content-length"}

_MESSAGE_KIND_BY_MEDIA_KIND = {None: MessageKind.TEXT, "audio": MessageKind.AUDIO, "image": MessageKind.IMAGE}

_HANDOFF_ACK_MESSAGE = "Entendido! Vou te transferir para um atendente humano, que vai continuar por aqui em breve."


async def _handoff_to_human(
    db: AsyncSession, instance: Instance, parsed: ParsedInboundMessage, thread: ConversationThread
) -> None:
    """Sends the canned handoff acknowledgement, records it, and pauses+flags the thread as
    needing human attention. No AI call involved - safe to run even without a configured
    provider or remaining daily budget."""
    await send_reply(instance, parsed.sender_number, _HANDOFF_ACK_MESSAGE, parsed.whatsbotmais_token)
    db.add(
        ConversationMessage(
            instance_id=instance.id,
            sender_number=parsed.sender_number,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.TEXT,
            text=_HANDOFF_ACK_MESSAGE,
        )
    )
    thread.ai_paused = True
    thread.escalated = True
    await db.commit()
    logger.info(
        "Instance %s: customer requested human handoff for %s, pausing AI", instance.id, parsed.sender_number
    )


async def _maybe_auto_reply(
    db: AsyncSession, instance: Instance, parsed: ParsedInboundMessage, thread: ConversationThread
) -> None:
    """Best-effort: generates and sends a WhatsApp reply for an inbound customer message.
    Never raises - failures are logged so the webhook call always succeeds for the sender."""
    if not instance.whatsapp_instance_name or instance.status != InstanceStatus.ACTIVE:
        return
    if thread.ai_paused:
        return

    try:
        # Checked before the AI budget/provider gates below: a customer explicitly asking for a
        # human should hand off even if the AI isn't configured or the daily budget is spent.
        if parsed.media_kind != "audio" and customer_requests_handoff(parsed.text):
            await _handoff_to_human(db, instance, parsed, thread)
            return

        used_today = await get_usage_today(db, instance.id)
        if used_today >= get_daily_limit(instance):
            logger.warning("Instance %s hit its daily AI assist budget; skipping auto-reply", instance.id)
            return

        provider = await get_ai_assist_provider(db)
        if not provider.is_configured:
            logger.warning("AI assist provider not configured; skipping auto-reply for instance %s", instance.id)
            return

        system_prompt = await get_current_prompt_content(db, instance)
        if not system_prompt:
            logger.warning("Instance %s has no saved prompt; skipping auto-reply", instance.id)
            return

        image_url: str | None = None
        log_prefix = "[atendimento]"
        message_text = parsed.text
        if parsed.media_kind == "audio":
            assert parsed.media_url is not None
            message_text = await provider.transcribe(parsed.media_url)
            log_prefix = "[atendimento-audio]"
        elif parsed.media_kind == "image":
            image_url = parsed.media_url
            message_text = parsed.text or "(imagem sem legenda)"
            log_prefix = "[atendimento-imagem]"

        # Re-checked here (in addition to the early text/image-caption check above) because an
        # audio message's handoff request only becomes visible after transcription.
        if parsed.media_kind == "audio" and customer_requests_handoff(message_text):
            await _handoff_to_human(db, instance, parsed, thread)
            return

        reply, prompt_tokens, completion_tokens = await provider.reply(
            system_prompt, [], message_text, image_url=image_url
        )
        reply, escalate = split_escalation_tag(reply)

        await send_reply(instance, parsed.sender_number, reply, parsed.whatsbotmais_token)

        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number=parsed.sender_number,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT,
                text=reply,
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
            logger.info("Instance %s: AI escalated conversation with %s", instance.id, parsed.sender_number)
        await db.commit()
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
    await db.commit()

    if parsed is not None and thread is not None:
        background_tasks.add_task(
            dispatch_event,
            instance.id,
            MESSAGE_RECEIVED,
            {"sender_number": parsed.sender_number, "text": parsed.text, "media_kind": parsed.media_kind},
        )
        was_escalated = thread.escalated
        await _maybe_auto_reply(db, instance, parsed, thread)
        if thread.escalated and not was_escalated:
            background_tasks.add_task(
                dispatch_event, instance.id, THREAD_ESCALATED, {"sender_number": parsed.sender_number}
            )
        # Fire-and-forget: re-analyzes the thread (extracts business data/FAQs/patterns and,
        # if configured, auto-generates a pending prompt) once enough new messages piled up.
        background_tasks.add_task(maybe_trigger_analysis, instance.id, parsed.sender_number)

    return {"received": True}


@router.get(
    "/{webhook_token}/prompt",
    response_model=InstancePromptOut,
    dependencies=[Depends(rate_limit_webhook_token)],
)
async def get_active_prompt(
    instance: Instance = Depends(get_instance_by_webhook_token),
    db: AsyncSession = Depends(get_db),
) -> InstancePromptOut:
    prompt = ""
    version_number = None
    if instance.current_prompt_version_id is not None:
        version = await db.get(PromptVersion, instance.current_prompt_version_id)
        if version is not None:
            prompt = version.content
            version_number = version.version_number

    return InstancePromptOut(
        instance_id=instance.id,
        name=instance.name,
        status=instance.status,
        prompt=prompt,
        version_number=version_number,
    )
