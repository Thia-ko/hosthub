import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SatisfactionResponse(Base):
    """One CSAT request/response cycle for a customer thread. Created when
    app.services.csat sends the satisfaction question after the thread has gone quiet
    following our last reply; `rating`/`response_text`/`responded_at` stay null until the
    customer answers (app.services.csat.try_capture)."""

    __tablename__ = "satisfaction_responses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    sender_number: Mapped[str] = mapped_column(String, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
