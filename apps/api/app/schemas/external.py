import uuid
from datetime import datetime

from pydantic import BaseModel


class ExternalDataItem(BaseModel):
    key: str
    value: str


class ExternalFaqItem(BaseModel):
    question: str
    answer: str


class ExternalDataOut(BaseModel):
    instance_id: uuid.UUID
    business_info: list[ExternalDataItem]
    products_services: list[ExternalDataItem]
    policies: list[ExternalDataItem]
    faqs: list[ExternalFaqItem]


class ExternalSendMessageRequest(BaseModel):
    to: str
    text: str


class ExternalMessageOut(BaseModel):
    id: uuid.UUID
    to: str
    text: str
    created_at: datetime
