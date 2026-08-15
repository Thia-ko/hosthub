import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConversationAnalysis(Base):
    """Records one AI analysis run over a customer thread (all `ConversationMessage` rows for
    an instance+sender_number). Used to avoid re-analyzing the same messages repeatedly and to
    count "analyzed conversations" for readiness checks and auto prompt generation triggers."""

    __tablename__ = "conversation_analyses"
    __table_args__ = (Index("ix_conversation_analyses_instance_sender", "instance_id", "sender_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    sender_number: Mapped[str] = mapped_column(String, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
