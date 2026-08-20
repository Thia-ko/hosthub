import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueueEventType(str, enum.Enum):
    QUEUED = "queued"  # entered QUEUED, whether first time or reopened after RESOLVED
    CLAIMED = "claimed"
    RESOLVED = "resolved"


class QueueEvent(Base):
    """Append-only audit trail of `ConversationThread.queue_status` transitions - the raw
    material for future wait-time/resolution-time stats (`app.services.dashboard_stats` has no
    queue metrics yet; this table exists so they can be added without a data migration once
    there's enough real usage to make routing/SLA decisions evidence-based)."""

    __tablename__ = "queue_events"
    __table_args__ = (Index("ix_queue_events_thread_id", "thread_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversation_threads.id"), nullable=False
    )
    event_type: Mapped[QueueEventType] = mapped_column(Enum(QueueEventType, name="queue_event_type"), nullable=False)
    agent_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
