import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttendantPattern(Base):
    """A behavioral pattern (greeting, tone, closing, objection handling, escalation, upsell)
    or personality trait (pattern_type="personality_trait") detected across analyzed
    conversations. `examples` is a JSON-encoded array of verbatim snippets, capped at 10."""

    __tablename__ = "attendant_patterns"
    __table_args__ = (Index("ix_attendant_patterns_instance_type", "instance_id", "pattern_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    pattern_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    examples: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
