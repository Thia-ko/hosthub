import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KnowledgeFileKind(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class KnowledgeFileUsageMode(str, enum.Enum):
    AUTO = "auto"  # always included when building AI context - "deixar o agente definir"
    MANUAL = "manual"  # only included for the next generation when include_next is toggled on,
    # then auto-resets to False after being consumed - "caso singular"
    DISABLED = "disabled"  # stored, never included


class KnowledgeFileStatus(str, enum.Enum):
    READY = "ready"
    PROCESSING_FAILED = "processing_failed"  # AI captioning/transcription failed - file is kept,
    # content_text stays null/stale, admin can still edit content_text manually


class InstanceKnowledgeFile(Base):
    """A file (text/image/audio/video) uploaded as reference material for an instance's AI
    agent. Image/audio uploads are auto-captioned/transcribed into `content_text` on upload;
    text uploads are decoded directly; video uploads wait for a manual `content_text`. Only
    rows with non-null `content_text` and an eligible `usage_mode` are folded into the prompt
    generation pipeline (see `app.services.knowledge_files.build_knowledge_section`)."""

    __tablename__ = "instance_knowledge_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[KnowledgeFileKind] = mapped_column(Enum(KnowledgeFileKind, name="knowledge_file_kind"), nullable=False)
    usage_mode: Mapped[KnowledgeFileUsageMode] = mapped_column(
        Enum(KnowledgeFileUsageMode, name="knowledge_file_usage_mode"),
        nullable=False,
        default=KnowledgeFileUsageMode.AUTO,
    )
    include_next: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[KnowledgeFileStatus] = mapped_column(
        Enum(KnowledgeFileStatus, name="knowledge_file_status"), nullable=False, default=KnowledgeFileStatus.READY
    )
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
