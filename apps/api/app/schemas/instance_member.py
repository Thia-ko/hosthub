import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.instance_member import InstanceMemberRole


class InstanceMemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: InstanceMemberRole
    created_at: datetime


class InstanceMembersOut(BaseModel):
    members: list[InstanceMemberOut]
    can_manage: bool


class InstanceMemberInviteRequest(BaseModel):
    email: str
    full_name: str
    password: str | None = None


class InstanceMemberInviteResponse(BaseModel):
    member: InstanceMemberOut
    generated_password: str | None = None
