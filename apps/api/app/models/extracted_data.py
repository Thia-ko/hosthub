import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExtractedData(Base):
    """A single fact (business info, product/service, or policy) mined from analyzed
    conversations for an instance. Upserted by key on every re-analysis: the merge keeps
    whichever value carries the higher confidence and bumps `occurrences` either way."""

    __tablename__ = "extracted_data"
    __table_args__ = (
        UniqueConstraint("instance_id", "category", "key", name="uq_extracted_data_instance_category_key"),
        Index("ix_extracted_data_instance_category", "instance_id", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
