import uuid

from pydantic import BaseModel

from app.models.instance import InstanceStatus


class InstancePromptOut(BaseModel):
    instance_id: uuid.UUID
    name: str
    status: InstanceStatus
    prompt: str
    version_number: int | None
