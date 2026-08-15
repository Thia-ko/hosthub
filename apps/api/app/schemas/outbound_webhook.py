import uuid
from datetime import datetime

from pydantic import BaseModel


class OutboundWebhookSubscriptionOut(BaseModel):
    id: uuid.UUID
    url: str
    events: list[str]
    active: bool
    created_at: datetime


class OutboundWebhookSubscriptionCreateRequest(BaseModel):
    url: str
    events: list[str]


class OutboundWebhookSubscriptionUpdateRequest(BaseModel):
    url: str | None = None
    events: list[str] | None = None
    active: bool | None = None
