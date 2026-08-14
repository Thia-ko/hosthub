from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.conversation_message import ConversationMessage
from app.models.instance import Instance
from app.schemas.conversation import ConversationMessageOut, ConversationSummary

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
        select(latest, ranked.c.message_count)
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
        )
        for message, message_count in result.all()
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
