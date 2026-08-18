import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.instance import InstanceStatus, WhatsAppProvider


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
    whatsapp_provider: WhatsAppProvider | None
    meta_phone_number_id: str | None
    auto_generate_prompt: bool
    auto_gen_conversation_threshold: int
    auto_gen_interval: str
    last_auto_gen_at: datetime | None


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
    whatsapp_provider: WhatsAppProvider | None = None
    auto_generate_prompt: bool | None = None
    auto_gen_conversation_threshold: int | None = None
    auto_gen_interval: str | None = None


class ClientPasswordResetOut(BaseModel):
    client_email: str
    generated_password: str
