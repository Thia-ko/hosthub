import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyOut(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str
    scopes: list[str]


class ApiKeyCreatedOut(ApiKeyOut):
    # Raw secret, present only in the create response - unrecoverable afterwards.
    key: str
