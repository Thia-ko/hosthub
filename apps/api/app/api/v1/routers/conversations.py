from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance
from app.schemas.conversation import ConversationMessageOut, ConversationReplyRequest, ConversationSummary
from app.services.conversation_threads import get_or_create_thread
from app.services.whatsapp_channel import WhatsAppChannelError, send_reply

router = APIRouter(prefix="/instances/{instance_id}/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationSummary])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationSummary]:
    """One row per customer phone number, showing their most recent message and total count -
    the standard "latest row per group" pattern via window functions, robust to timestamp ties."""
    row_number = func.row_number().over(
        partition_by=ConversationMessage.sender_number, order_by=ConversationMessage.created_at.desc()
    )
    message_count = func.count().over(partition_by=ConversationMessage.sender_number)
    ranked = (
        select(ConversationMessage, row_number.label("rn"), message_count.label("message_count"))
        .where(ConversationMessage.instance_id == instance.id)
        .subquery()
    )
    latest = aliased(ConversationMessage, ranked)

    result = await db.execute(
        select(latest, ranked.c.message_count, ConversationThread.ai_paused, ConversationThread.escalated)
        .outerjoin(
            ConversationThread,
            (ConversationThread.instance_id == instance.id)
            & (ConversationThread.sender_number == ranked.c.sender_number),
        )
        .where(ranked.c.rn == 1)
        .order_by(ranked.c.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [
        ConversationSummary(
            sender_number=message.sender_number,
            last_message_text=message.text,
            last_message_kind=message.kind,
            last_direction=message.direction,
            last_message_at=message.created_at,
            message_count=message_count,
            ai_paused=bool(ai_paused),
            escalated=bool(escalated),
        )
        for message, message_count, ai_paused, escalated in result.all()
    ]


@router.get("/{sender_number}", response_model=list[ConversationMessageOut])
async def get_conversation_thread(
    sender_number: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationMessage]:
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.instance_id == instance.id, ConversationMessage.sender_number == sender_number)
        .order_by(ConversationMessage.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.post("/{sender_number}/reply", response_model=ConversationMessageOut)
async def reply_to_conversation(
    sender_number: str,
    payload: ConversationReplyRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> ConversationMessage:
    """Manual human takeover: sends a message on the instance's WhatsApp channel and pauses
    the AI auto-reply for this thread, since a human is now handling it directly."""
    thread = await get_or_create_thread(db, instance.id, sender_number)
    try:
        await send_reply(instance, sender_number, payload.text, thread.last_whatsbotmais_token)
    except WhatsAppChannelError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    message = ConversationMessage(
        instance_id=instance.id,
        sender_number=sender_number,
        direction=MessageDirection.OUTBOUND,
        kind=MessageKind.TEXT,
        text=payload.text,
    )
    db.add(message)
    thread.ai_paused = True
    thread.escalated = False
    await db.commit()
    await db.refresh(message)
    return message


@router.post("/{sender_number}/pause", response_model=dict)
async def pause_conversation(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    thread = await get_or_create_thread(db, instance.id, sender_number)
    thread.ai_paused = True
    await db.commit()
    return {"ai_paused": True, "escalated": thread.escalated}


@router.post("/{sender_number}/resume", response_model=dict)
async def resume_conversation(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    thread = await get_or_create_thread(db, instance.id, sender_number)
    thread.ai_paused = False
    thread.escalated = False
    await db.commit()
    return {"ai_paused": False, "escalated": False}
