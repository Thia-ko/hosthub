import uuid
from datetime import datetime

from pydantic import BaseModel


class PromptTemplateOut(BaseModel):
    id: uuid.UUID
    niche: str
    title: str
    description: str
    icon_emoji: str | None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PromptTemplateCreateRequest(BaseModel):
    niche: str
    title: str
    description: str
    icon_emoji: str | None = None
    content: str


class PromptTemplateUpdateRequest(BaseModel):
    niche: str | None = None
    title: str | None = None
    description: str | None = None
    icon_emoji: str | None = None
    content: str | None = None
