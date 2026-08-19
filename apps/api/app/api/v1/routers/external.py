from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_key_auth import require_scope
from app.db.session import get_db
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.instance import Instance
from app.schemas.external import ExternalDataOut, ExternalMessageOut, ExternalSendMessageRequest
from app.schemas.instance_prompt import InstancePromptOut
from app.services.api_keys import DATA_READ, MESSAGES_WRITE, PROMPT_READ
from app.services.conversation_threads import get_or_create_thread
from app.services.prompt_content import get_current_prompt_version
from app.services.prompt_generator import get_collected_data
from app.services.whatsapp_channel import WhatsAppChannelError, send_reply

router = APIRouter(prefix="/external", tags=["external-api"])


@router.get("/prompt", response_model=InstancePromptOut)
async def get_prompt(
    instance: Instance = Depends(require_scope(PROMPT_READ)), db: AsyncSession = Depends(get_db)
) -> InstancePromptOut:
    """The instance's current live prompt - same content app.api.v1.routers.webhooks serves at
    /webhooks/{webhook_token}/prompt, but behind a scoped, revocable API key instead of the
    dual-purpose webhook token, for integrations that shouldn't also be able to inject inbound
    webhook events."""
    version = await get_current_prompt_version(db, instance)
    return InstancePromptOut(
        instance_id=instance.id,
        name=instance.name,
        status=instance.status,
        prompt=version.content if version else "",
        version_number=version.version_number if version else None,
    )


@router.get("/data", response_model=ExternalDataOut)
async def get_data(
    instance: Instance = Depends(require_scope(DATA_READ)), db: AsyncSession = Depends(get_db)
) -> ExternalDataOut:
    """The same collected data (business info, products/services, policies, FAQs) used to build
    the generated prompt - see app.services.prompt_generator.get_collected_data."""
    data = await get_collected_data(db, instance.id)
    return ExternalDataOut(instance_id=instance.id, **data)


@router.post("/messages", response_model=ExternalMessageOut)
async def send_message(
    payload: ExternalSendMessageRequest,
    instance: Instance = Depends(require_scope(MESSAGES_WRITE)),
    db: AsyncSession = Depends(get_db),
) -> ExternalMessageOut:
    """Sends a WhatsApp message on the instance's channel on behalf of an external system (n8n,
    a client's own backend) and pauses AI auto-reply for the thread - same effect as a human
    manual reply (app.api.v1.routers.conversations.reply_to_conversation): an external system
    taking over a conversation should stop the AI from replying into it too."""
    thread = await get_or_create_thread(db, instance.id, payload.to)
    try:
        await send_reply(instance, payload.to, payload.text, thread.last_whatsbotmais_token)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    message = ConversationMessage(
        instance_id=instance.id,
        sender_number=payload.to,
        direction=MessageDirection.OUTBOUND,
        kind=MessageKind.TEXT,
        text=payload.text,
        origin=MessageOrigin.API,
    )
    db.add(message)
    thread.ai_paused = True
    thread.escalated = False
    await db.commit()
    await db.refresh(message)
    return ExternalMessageOut(id=message.id, to=message.sender_number, text=message.text, created_at=message.created_at)
