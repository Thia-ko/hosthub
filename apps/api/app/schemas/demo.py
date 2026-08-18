import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DemoChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DemoChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=300)
    history: list[DemoChatHistoryItem] = Field(default_factory=list, max_length=12)


class DemoChatResponse(BaseModel):
    reply: str
    messages_remaining: int


class DemoLeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact: str = Field(min_length=1, max_length=200)
    business_name: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=1000)


class DemoLeadOut(BaseModel):
    id: uuid.UUID
    name: str
    contact: str
    business_name: str | None
    note: str | None
    created_at: datetime
    contacted_at: datetime | None


class DemoLeadContactedUpdate(BaseModel):
    contacted: bool
