import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.prompt_version import PromptVersionSource


class PromptVersionSummary(BaseModel):
    id: uuid.UUID
    version_number: int
    source: PromptVersionSource
    change_note: str | None
    created_by_user_id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptVersionDetail(PromptVersionSummary):
    content: str


class PromptVersionCreateRequest(BaseModel):
    content: str
    change_note: str | None = None
    source: Literal["manual", "template"] = "manual"


class PromptVersionDiffSide(BaseModel):
    version_number: int
    content: str


class PromptVersionDiffResponse(BaseModel):
    from_: PromptVersionDiffSide = Field(alias="from")
    to: PromptVersionDiffSide

    model_config = {"populate_by_name": True}
