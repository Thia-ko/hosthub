import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AgentAvailability(str, enum.Enum):
    """Self-reported presence for the attendance queue - there's no connection/heartbeat
    tracking, so this only ever reflects what the agent last toggled explicitly. `ONLINE`/`BUSY`
    both show up as claim-eligible in the UI (BUSY just warns before claiming); `AWAY`/`OFFLINE`
    hide the agent from "who's around" without blocking them from opening `/app/filas` directly."""

    ONLINE = "online"
    BUSY = "busy"
    AWAY = "away"
    OFFLINE = "offline"


class AgentProfile(Base):
    """One row per (instance, user) that has ever set a queue availability status. Created
    lazily by `app.services.queue.get_or_create_agent_profile` on first status write - most
    instance members never touch this and simply don't show up in the "quem está por perto"
    strip until they do."""

    __tablename__ = "agent_profiles"
    __table_args__ = (UniqueConstraint("instance_id", "user_id", name="uq_agent_profiles_instance_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[AgentAvailability] = mapped_column(
        Enum(AgentAvailability, name="agent_availability"), nullable=False, default=AgentAvailability.OFFLINE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
