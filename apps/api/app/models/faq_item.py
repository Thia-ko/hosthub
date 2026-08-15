import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FaqItem(Base):
    """A frequently asked question mined from analyzed conversations. Re-analysis merges
    near-duplicate questions (Jaccard similarity on the first 60 chars) into the same row
    instead of creating a new one, bumping `frequency`."""

    __tablename__ = "faq_items"
    __table_args__ = (Index("ix_faq_items_instance_category", "instance_id", "category"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False, default="geral")
    asked_by: Mapped[str] = mapped_column(String, nullable=False, default="cliente")
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
