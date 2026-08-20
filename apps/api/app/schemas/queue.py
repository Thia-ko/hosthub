import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.agent_profile import AgentAvailability
from app.models.conversation_thread import EscalationReason, QueueStatus
from app.schemas.conversation import ConversationMessageOut


class QueueItemAgentOut(BaseModel):
    id: uuid.UUID
    full_name: str


class QueueItemQueueOut(BaseModel):
    id: uuid.UUID
    name: str
    color: str


class QueueItemOut(BaseModel):
    sender_number: str
    queue_status: QueueStatus
    escalation_reason: EscalationReason | None
    ai_confidence: int | None
    # Derived at read time (app.services.queue.compute_priority/compute_sla_risk), not stored.
    priority: str
    sla_risk: str
    wait_time_seconds: int
    queued_at: datetime | None
    assigned_at: datetime | None
    resolved_at: datetime | None
    assigned_agent: QueueItemAgentOut | None
    queue: QueueItemQueueOut | None
    last_message_preview: str
    last_message_at: datetime


class QueueReassignRequest(BaseModel):
    queue_id: uuid.UUID


class QueueContextOut(BaseModel):
    sender_number: str
    intent_summary: str | None
    escalation_reason: EscalationReason | None
    ai_confidence: int | None
    recent_messages: list[ConversationMessageOut]


class AgentProfileOut(BaseModel):
    user_id: uuid.UUID
    full_name: str
    status: AgentAvailability


class AgentStatusUpdateRequest(BaseModel):
    status: AgentAvailability
