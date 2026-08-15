import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PromptVersionSource(str, enum.Enum):
    MANUAL = "manual"
    AI_ASSIST = "ai_assist"
    TEMPLATE = "template"
    AUTO_GENERATED = "auto_generated"


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = (UniqueConstraint("instance_id", "version_number", name="uq_prompt_version_instance_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[PromptVersionSource] = mapped_column(
        Enum(PromptVersionSource, name="prompt_version_source"), nullable=False, default=PromptVersionSource.MANUAL
    )
    change_note: Mapped[str | None] = mapped_column(String, nullable=True)
    is_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
