import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WebhookEventOut(BaseModel):
    id: uuid.UUID
    payload_json: Any
    received_at: datetime

    model_config = {"from_attributes": True}
