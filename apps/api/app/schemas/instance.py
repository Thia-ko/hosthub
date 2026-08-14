import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.instance import InstanceStatus


class InstanceOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    status: InstanceStatus
    owner_user_id: uuid.UUID
    owner_email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InstanceDetailOut(InstanceOut):
    ai_assist_daily_token_limit: int | None
    webhook_token: str
    whatsapp_instance_name: str | None


class InstanceCreateRequest(BaseModel):
    name: str
    client_email: str
    client_full_name: str
    client_password: str | None = None


class InstanceCreateResponse(BaseModel):
    instance: InstanceDetailOut
    client_email: str
    generated_password: str | None = None


class InstanceUpdateRequest(BaseModel):
    name: str | None = None
    status: InstanceStatus | None = None
    ai_assist_daily_token_limit: int | None = None
    whatsapp_instance_name: str | None = None


class ClientPasswordResetOut(BaseModel):
    client_email: str
    generated_password: str
