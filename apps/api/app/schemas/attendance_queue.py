import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.attendance_queue import QueueBasePriority


class AttendanceQueueOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    routing_hint: str | None
    keywords: str | None
    base_priority: QueueBasePriority
    color: str
    position: int
    is_default: bool
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendanceQueueCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    routing_hint: str | None = Field(default=None, max_length=500)
    keywords: str | None = Field(default=None, max_length=500)
    base_priority: QueueBasePriority = QueueBasePriority.NORMAL
    color: str = Field(default="#64748b", pattern=r"^#[0-9a-fA-F]{6}$")


class AttendanceQueueUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    routing_hint: str | None = Field(default=None, max_length=500)
    keywords: str | None = Field(default=None, max_length=500)
    base_priority: QueueBasePriority | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    active: bool | None = None


class AttendanceQueueReorderRequest(BaseModel):
    # Full ordered list of queue ids for the instance - simpler and less error-prone than a
    # single up/down swap endpoint, at the cost of the client sending every id on each reorder.
    ordered_ids: list[uuid.UUID]
