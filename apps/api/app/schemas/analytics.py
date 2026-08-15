import uuid
from datetime import datetime

from pydantic import BaseModel


class ExtractedDataOut(BaseModel):
    id: uuid.UUID
    category: str
    key: str
    value: str
    confidence: float
    occurrences: int
    source: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExtractedDataCreateRequest(BaseModel):
    category: str
    key: str
    value: str


class ExtractedDataUpdateRequest(BaseModel):
    value: str


class FaqItemOut(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    category: str
    asked_by: str
    frequency: int
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FaqCreateRequest(BaseModel):
    question: str
    answer: str
    category: str = "geral"
    asked_by: str = "cliente"


class FaqUpdateRequest(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None


class AttendantPatternOut(BaseModel):
    id: uuid.UUID
    pattern_type: str
    description: str
    examples: list[str]
    frequency: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnalyticsOverviewOut(BaseModel):
    analyzed_conversations: int
    total_faqs: int
    total_extracted: int
    total_patterns: int
    pending_prompt: bool


class DataReadinessOut(BaseModel):
    analyzed_conversations: int
    total_faqs: int
    total_extracted: int
    total_patterns: int
    ready: bool


class GeneratedPromptOut(BaseModel):
    id: uuid.UUID
    version_number: int
    content: str
    change_note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
