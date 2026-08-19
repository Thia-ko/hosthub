import uuid
from datetime import datetime

from pydantic import BaseModel


class ChatbotNodeOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    label: str
    keywords: list[str]
    message: str
    order_index: int
    created_at: datetime


class ChatbotNodeCreateRequest(BaseModel):
    # None creates the root (the greeting + main menu) - only one is allowed per instance.
    parent_id: uuid.UUID | None = None
    label: str
    keywords: list[str] = []
    message: str
    order_index: int = 0


class ChatbotNodeUpdateRequest(BaseModel):
    label: str | None = None
    keywords: list[str] | None = None
    message: str | None = None
    order_index: int | None = None
