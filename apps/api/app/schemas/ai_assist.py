import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class AiAssistUsageOut(BaseModel):
    used_today: int
    limit: int
    resets_at: datetime


class AiAssistSuggestRequest(BaseModel):
    instruction: str


class AiAssistSuggestResponse(BaseModel):
    ai_assist_request_id: uuid.UUID
    suggested_content: str
    prompt_tokens: int
    completion_tokens: int


class SandboxMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AiAssistSandboxReplyRequest(BaseModel):
    message: str
    prompt_override: str | None = None
    history: list[SandboxMessage] = []


class AiAssistSandboxReplyResponse(BaseModel):
    reply: str
    prompt_tokens: int
    completion_tokens: int
