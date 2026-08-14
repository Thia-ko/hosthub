from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AiSettingsOut(BaseModel):
    base_url: str
    model: str
    transcribe_model: str
    # Whether the effective API key comes from the admin panel (DB), the AI_ASSIST_API_KEY env
    # var, or isn't set anywhere. The key itself is never sent back to the browser.
    api_key_source: Literal["database", "env", "none"]
    updated_at: datetime | None = None


class AiSettingsUpdateRequest(BaseModel):
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    transcribe_model: str = Field(min_length=1)
    # Omitted/null: leave the currently stored key untouched. Non-empty: replace it.
    api_key: str | None = None
    # Explicit removal of the DB-stored key (falls back to AI_ASSIST_API_KEY env var, if any).
    # Takes precedence over `api_key` when both are sent.
    clear_api_key: bool = False
