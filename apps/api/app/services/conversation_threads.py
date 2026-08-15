import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_thread import ConversationThread


async def get_or_create_thread(db: AsyncSession, instance_id: uuid.UUID, sender_number: str) -> ConversationThread:
    """Fetches the (instance_id, sender_number) thread row, creating it on first contact.
    Caller is responsible for `commit`/`flush` as appropriate for its own transaction."""
    thread = await db.scalar(
        select(ConversationThread).where(
            ConversationThread.instance_id == instance_id, ConversationThread.sender_number == sender_number
        )
    )
    if thread is None:
        thread = ConversationThread(instance_id=instance_id, sender_number=sender_number)
        db.add(thread)
        await db.flush()
    return thread
