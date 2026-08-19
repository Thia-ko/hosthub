import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConversationThread(Base):
    """Per-customer conversation state for an instance, keyed by (instance_id, sender_number).

    Created lazily on the first inbound message and updated on every subsequent one.
    `last_whatsbotmais_token` caches the token WhatsBotMais includes on each inbound webhook -
    outside of that reactive flow (manual reply, future campaigns) there is no other way to
    address a WhatsBotMais conversation, since the provider issues no per-instance credential.
    `ai_paused` gates every automated reply engine (AI or chatbot, see app.services.chatbot):
    set automatically when a human sends a manual reply or the conversation auto-escalates,
    toggled explicitly via the pause/resume endpoints.
    `escalated` distinguishes "auto-paused because the customer/AI flagged it needs a human"
    (app.services.escalation) from "a human chose to pause it themselves" - the UI badges them
    differently. Cleared whenever a human resumes or replies (they've now engaged).
    `csat_requested_at` marks when app.services.csat last sent the satisfaction question for
    this thread, so it isn't re-sent on every scheduler tick while awaiting a reply.
    `chatbot_node_id` is this customer's current position in app.services.chatbot's tree - null
    means "not started / back at the root". Cleared automatically if that node is deleted (ON
    DELETE SET NULL), which simply restarts their session on the next message.
    """

    __tablename__ = "conversation_threads"
    __table_args__ = (UniqueConstraint("instance_id", "sender_number", name="uq_conversation_threads_instance_sender"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    sender_number: Mapped[str] = mapped_column(String, nullable=False)
    last_whatsbotmais_token: Mapped[str | None] = mapped_column(String, nullable=True)
    ai_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    csat_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    chatbot_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbot_nodes.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
