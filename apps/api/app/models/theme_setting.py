import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

DEFAULT_LIGHT_PRIMARY = "#008757"
DEFAULT_LIGHT_SECONDARY = "#C7EBD8"
DEFAULT_DARK_PRIMARY = "#2ACC8F"
DEFAULT_DARK_SECONDARY = "#0E2D20"

SINGLETON_ID = 1


class ThemeSetting(Base):
    __tablename__ = "theme_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=SINGLETON_ID)
    light_primary_color: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_LIGHT_PRIMARY)
    light_secondary_color: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_LIGHT_SECONDARY)
    dark_primary_color: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_DARK_PRIMARY)
    dark_secondary_color: Mapped[str] = mapped_column(String, nullable=False, default=DEFAULT_DARK_SECONDARY)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
