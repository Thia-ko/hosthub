import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstanceMemberRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


class InstanceMember(Base):
    """Grants a user access to an instance, beyond the original `Instance.owner_user_id`.

    Every instance always has exactly one OWNER row (created alongside the instance, and
    backfilled from `owner_user_id` for pre-existing rows by migration 0015) plus zero or more
    MEMBER rows invited later by the admin or the owner. `app.core.deps.get_owned_instance`
    checks membership here instead of comparing `owner_user_id` directly, so members see and
    use the instance exactly like the owner - there's a single client access level, OWNER only
    matters for who can manage the team (invite/remove) and can never be removed down to zero.
    """

    __tablename__ = "instance_members"
    __table_args__ = (UniqueConstraint("instance_id", "user_id", name="uq_instance_members_instance_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[InstanceMemberRole] = mapped_column(
        Enum(InstanceMemberRole, name="instance_member_role"), nullable=False, default=InstanceMemberRole.MEMBER
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
