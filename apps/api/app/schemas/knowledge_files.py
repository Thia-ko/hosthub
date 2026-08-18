import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.instance_knowledge_file import KnowledgeFileKind, KnowledgeFileStatus, KnowledgeFileUsageMode


class KnowledgeFileOut(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    kind: KnowledgeFileKind
    usage_mode: KnowledgeFileUsageMode
    include_next: bool
    status: KnowledgeFileStatus
    size_bytes: int
    content_text: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeFileUpdateRequest(BaseModel):
    usage_mode: KnowledgeFileUsageMode | None = None
    include_next: bool | None = None
    content_text: str | None = None
