import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.campaign import CampaignStatus


class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    message: str
    status: CampaignStatus
    total_recipients: int
    sent_count: int
    skipped_count: int
    failed_count: int
    created_at: datetime


class CampaignCreateRequest(BaseModel):
    name: str
    message: str
