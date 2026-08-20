import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueueStatus(str, enum.Enum):
    """Where a thread sits relative to the human attendance queue (`app.services.queue`).
    NONE: no human queue involvement (AI handling it, or nobody ever escalated it).
    QUEUED: escalated and waiting for an agent to claim (pull model - no auto-assignment).
    IN_PROGRESS: an agent claimed it and is actively engaged.
    ON_HOLD: the assigned agent is waiting on the customer, not stalled on their own end.
    RESOLVED: the assigned agent marked it done. A new inbound message reopens it to QUEUED
    (see `app.services.queue.reopen_if_resolved`) regardless of `ai_paused`, since resolving
    doesn't hand control back to the AI - only the separate resume endpoint does that.
    """

    NONE = "none"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    RESOLVED = "resolved"


class EscalationReason(str, enum.Enum):
    """Why a thread entered the queue - mirrors the three triggers in `app.services.escalation`
    and `app.services.queue`: the customer asked for a human by keyword, the AI itself flagged
    uncertainty/sensitivity via the `[ESCALAR]` tag, or the AI provider call itself failed
    (timeout/rate limit/5xx/malformed response - see `app.services.queue.escalate_for_ai_failure`,
    called from `app.services.ai_reply.try_reply`)."""

    CUSTOMER_REQUEST = "customer_request"
    AI_UNCERTAIN = "ai_uncertain"
    AI_FAILURE = "ai_failure"


class ConversationThread(Base):
    """Per-customer conversation state for an instance, keyed by (instance_id, sender_number).

    Created lazily on the first inbound message and updated on every subsequent one. Fields
    below are grouped by the service that owns writing them (see `app.api.v1.routers.webhooks`
    etapa 1-3 decomposition: `app.services.queue`, `app.services.chatbot`, `app.services.csat`)
    - this is a single table, not one table per group, since splitting the two most-shared,
    hottest fields (`ai_paused`/`escalated`, read on every inbound message) would trade a
    readability win for a JOIN on the hot path with no matching ownership boundary to justify
    it. The grouping below is the map for "who's allowed to write this field", not a schema
    decision.

    `last_whatsbotmais_token` caches the token WhatsBotMais includes on each inbound webhook -
    outside of that reactive flow (manual reply, future campaigns) there is no other way to
    address a WhatsBotMais conversation, since the provider issues no per-instance credential.
    `ai_paused` gates every automated reply engine (AI or chatbot, see app.services.chatbot):
    set automatically when a human sends a manual reply or the conversation auto-escalates,
    toggled explicitly via the pause/resume endpoints.
    `escalated` distinguishes "auto-paused because the customer/AI flagged it needs a human"
    (app.services.escalation) from "a human chose to pause it themselves" - the UI badges them
    differently. Cleared whenever a human resumes or replies (they've now engaged). Left
    untouched by the queue lifecycle below (claim/hold/resolve) - `dashboard_stats` relies on
    its exact "awaiting a human who hasn't replied yet" meaning to compute AI resolution rate.
    `csat_requested_at` marks when app.services.csat last sent the satisfaction question for
    this thread, so it isn't re-sent on every scheduler tick while awaiting a reply.
    `chatbot_node_id` is this customer's current position in app.services.chatbot's tree - null
    means "not started / back at the root". Cleared automatically if that node is deleted (ON
    DELETE SET NULL), which simply restarts their session on the next message.

    The queue fields below (`queue_status` onward) are a layer on top of `ai_paused`/
    `escalated`, populated by `app.services.queue` and the queue router - see `QueueStatus` for
    the state machine. `escalation_reason`/`ai_confidence` are captured once at enqueue time and
    not updated afterwards (a thread only enqueues from a non-escalated state). `queue_id` points
    at the named `AttendanceQueue` this thread was routed into (see that model's docstring for
    the routing mechanism) - ON DELETE SET NULL so deleting a queue never orphans a thread's
    history, `app.services.queue` re-resolves it to the instance's default queue on next enqueue.
    """

    __tablename__ = "conversation_threads"
    __table_args__ = (UniqueConstraint("instance_id", "sender_number", name="uq_conversation_threads_instance_sender"),)

    # --- Identity --------------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    sender_number: Mapped[str] = mapped_column(String, nullable=False)
    last_whatsbotmais_token: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- Control state: shared - who's driving this conversation right now (AI, chatbot, or a
    # human). Written by app.services.queue (handoff/escalation), app.services.ai_reply (AI
    # escalation), and directly by app.api.v1.routers.conversations (manual reply/resume) and
    # app.api.v1.routers.external (API-driven reply). No single owner by design: this is the
    # join point between the three engines, not a domain's private state.
    ai_paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- Chatbot state: owned by app.services.chatbot -----------------------------------------
    chatbot_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbot_nodes.id", ondelete="SET NULL"), nullable=True
    )

    # --- Queue state: owned by app.services.queue and app.api.v1.routers.queue/attendance_queues
    queue_status: Mapped[QueueStatus] = mapped_column(
        Enum(QueueStatus, name="queue_status"), nullable=False, default=QueueStatus.NONE
    )
    escalation_reason: Mapped[EscalationReason | None] = mapped_column(
        Enum(EscalationReason, name="escalation_reason"), nullable=True
    )
    ai_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    queue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("attendance_queues.id", ondelete="SET NULL"), nullable=True
    )
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- CSAT state: owned by app.services.csat -----------------------------------------------
    csat_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Bookkeeping -----------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
