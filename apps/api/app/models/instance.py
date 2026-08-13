import enum
import secrets
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstanceStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class Instance(Base):
    __tablename__ = "instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_by_admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[InstanceStatus] = mapped_column(
        Enum(InstanceStatus, name="instance_status"), nullable=False, default=InstanceStatus.ACTIVE
    )
    webhook_token: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32)
    )
    ai_assist_daily_token_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
