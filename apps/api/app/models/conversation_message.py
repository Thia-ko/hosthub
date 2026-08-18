import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class MessageKind(str, enum.Enum):
    TEXT = "text"
    AUDIO = "audio"
    IMAGE = "image"


class MessageOrigin(str, enum.Enum):
    AI = "ai"
    HUMAN = "human"
    SYSTEM = "system"


class ConversationMessage(Base):
    """One message (customer or agent) in an instance's WhatsApp conversation history, keyed by
    the customer's phone number so the UI can group raw webhook traffic into per-customer threads."""

    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index("ix_conversation_messages_instance_sender_created", "instance_id", "sender_number", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    sender_number: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="message_direction"), nullable=False
    )
    kind: Mapped[MessageKind] = mapped_column(
        Enum(MessageKind, name="message_kind"), nullable=False, default=MessageKind.TEXT
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    media_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Who authored an OUTBOUND message: AI (auto-reply), HUMAN (manual takeover reply), or
    # SYSTEM (canned message - CSAT question/thanks, handoff acknowledgement, campaign
    # broadcast). Null for INBOUND (customer) messages and for OUTBOUND rows written before
    # this column existed. Used by dashboard_stats.get_resolution_stats to tell "the AI handled
    # this" apart from "a human had to step in".
    origin: Mapped[MessageOrigin | None] = mapped_column(
        Enum(MessageOrigin, name="message_origin"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
