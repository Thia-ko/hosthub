import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

SINGLETON_ID = 1


class AiSettings(Base):
    """Platform-wide AI assist provider config, editable by the admin from the UI (Configuracoes
    > IA). Any blank/unset field here falls back to the corresponding AI_ASSIST_* env var - see
    app.services.ai_settings.get_effective_ai_settings. Stored in plaintext like the rest of this
    app's credentials (webhook tokens, JWT secret); this table is admin-only (require_admin)."""

    __tablename__ = "ai_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=SINGLETON_ID)
    api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    transcribe_model: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
