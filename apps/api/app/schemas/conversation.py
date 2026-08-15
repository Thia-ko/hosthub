import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.conversation_message import MessageDirection, MessageKind


class ConversationMessageOut(BaseModel):
    id: uuid.UUID
    direction: MessageDirection
    kind: MessageKind
    text: str
    media_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    sender_number: str
    last_message_text: str
    last_message_kind: MessageKind
    last_direction: MessageDirection
    last_message_at: datetime
    message_count: int
    ai_paused: bool
    escalated: bool


class ConversationReplyRequest(BaseModel):
    text: str
