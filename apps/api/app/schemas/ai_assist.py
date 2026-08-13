import uuid
from datetime import datetime

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
