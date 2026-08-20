"""Pull-model attendance queue: threads escalate into QUEUED (see `app.services.escalation`),
an available agent claims one explicitly (no auto-assignment - see the v1 scope note in
docs/backlog), and the queue router (`app.api.v1.routers.queue`) exposes claim/hold/resolve as
plain state transitions. This module centralizes those transitions so both the queue router and
the plain conversations router (`reply_to_conversation`'s implicit claim, `resume_conversation`'s
reset) stay in sync without duplicating the `QueueEvent` bookkeeping.

Also owns routing into a named `AttendanceQueue` (`match_queue_by_keywords`,
`resolve_default_queue`, `resolve_queue_by_slug`, `to_escalation_options`) and, since it's the
same routing decision either way, the customer-initiated handoff step itself (`try_handoff`,
used by `app.api.v1.routers.webhooks._maybe_auto_reply` before the chatbot/AI paths, and
`app.services.ai_reply.try_reply`'s post-transcription re-check for audio messages) - combining
a queue's configured floor priority with the time-based escalation (`compute_priority`).

SLA risk is still derived at read time from `queued_at`, not stored - there's no per-instance
configuration for its thresholds yet, deliberately: tuning them needs real wait-time data this
table starts collecting, not a guess baked in on day one.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_profile import AgentAvailability, AgentProfile
from app.models.attendance_queue import AttendanceQueue, QueueBasePriority
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.conversation_thread import ConversationThread, EscalationReason, QueueStatus
from app.models.instance import Instance
from app.models.queue_event import QueueEvent, QueueEventType
from app.services.escalation import EscalationQueueOption, customer_requests_handoff
from app.services.whatsapp_channel import ParsedInboundMessage, send_reply

logger = logging.getLogger(__name__)

HANDOFF_ACK_MESSAGE = "Entendido! Vou te transferir para um atendente humano, que vai continuar por aqui em breve."
# Sent by app.services.ai_reply.try_reply -> escalate_for_ai_failure when the AI provider call
# itself fails (timeout, rate limit, 5xx, malformed response) - the customer must never see
# silence just because the provider had a bad moment.
AI_FAILURE_MESSAGE = (
    "Desculpe, estou com uma instabilidade tecnica no momento e nao consegui gerar uma resposta. "
    "Ja avisei nossa equipe - alguem vai te atender em instantes."
)

_HIGH_PRIORITY_WAIT_SECONDS = 300  # 5 min
_URGENT_PRIORITY_WAIT_SECONDS = 600  # 10 min
_SLA_WARNING_SECONDS = 120  # 2 min
_SLA_CRITICAL_SECONDS = 300  # 5 min

_PRIORITY_RANK = {"normal": 0, "high": 1, "urgent": 2}
_RANK_TO_PRIORITY = ("normal", "high", "urgent")


def compute_priority(
    escalation_reason: EscalationReason | None,
    wait_seconds: float,
    queue_base_priority: QueueBasePriority | str | None = None,
) -> str:
    """Combines three signals and takes the highest: the queue's own configured floor
    (`queue_base_priority` - an URGENT-tier queue never looks "normal" just because a card is
    fresh), a customer-requested handoff starting at "high", and wait-time escalation (a
    NORMAL-tier queue still climbs the longer it waits). Avoids a manual per-card triage field
    agents would have to keep fresh on top of actually working the queue."""
    base_value = queue_base_priority.value if isinstance(queue_base_priority, QueueBasePriority) else queue_base_priority
    rank = _PRIORITY_RANK.get(base_value or "normal", 0)
    if escalation_reason == EscalationReason.CUSTOMER_REQUEST:
        rank = max(rank, _PRIORITY_RANK["high"])
    if wait_seconds >= _URGENT_PRIORITY_WAIT_SECONDS:
        rank = max(rank, _PRIORITY_RANK["urgent"])
    elif wait_seconds >= _HIGH_PRIORITY_WAIT_SECONDS:
        rank = max(rank, _PRIORITY_RANK["high"])
    return _RANK_TO_PRIORITY[rank]


def compute_sla_risk(wait_seconds: float) -> str:
    """Purely visual (ring color/pulse speed in the queue panel) - not an enforced deadline."""
    if wait_seconds >= _SLA_CRITICAL_SECONDS:
        return "critical"
    if wait_seconds >= _SLA_WARNING_SECONDS:
        return "warning"
    return "ok"


async def enqueue_thread(
    db: AsyncSession,
    thread: ConversationThread,
    *,
    escalation_reason: EscalationReason,
    queue_id: uuid.UUID,
    ai_confidence: int | None = None,
) -> None:
    """Moves a thread into QUEUED, whether it's escalating for the first time or reopening after
    a prior RESOLVED. Leaves `assigned_agent_id` untouched so a reopen keeps the previous agent
    visible as a continuity hint in the queue card - re-claiming is still an explicit action,
    nothing here auto-assigns. `queue_id` is required: the caller must have already resolved one
    (`match_queue_by_keywords`/`resolve_queue_by_slug`, falling back to `resolve_default_queue`)
    - every instance always has a default queue, so there's never a legitimate "no queue" case."""
    thread.queue_status = QueueStatus.QUEUED
    thread.escalation_reason = escalation_reason
    thread.ai_confidence = ai_confidence
    thread.queue_id = queue_id
    thread.queued_at = datetime.now(timezone.utc)
    thread.resolved_at = None
    db.add(QueueEvent(thread_id=thread.id, event_type=QueueEventType.QUEUED))


def match_queue_by_keywords(queues: Sequence[AttendanceQueue], text: str) -> AttendanceQueue | None:
    """Deterministic routing for the customer-request handoff path, which never calls the AI:
    the first active queue (in position order) whose `keywords` (comma-separated phrases)
    contains a substring hit in `text`. None if nothing matches - the caller falls back to
    `resolve_default_queue`."""
    normalized = text.lower()
    for queue in queues:
        if not queue.active or not queue.keywords:
            continue
        phrases = [phrase.strip().lower() for phrase in queue.keywords.split(",") if phrase.strip()]
        if any(phrase in normalized for phrase in phrases):
            return queue
    return None


def resolve_default_queue(queues: Sequence[AttendanceQueue]) -> AttendanceQueue:
    """The instance's `is_default` queue - always present by construction (created alongside the
    instance, see `app.api.v1.routers.instances.create_instance`, and never deletable). Falls
    back to the first queue if that invariant were ever violated, rather than raising and
    breaking the whole escalation flow over a routing edge case."""
    for queue in queues:
        if queue.is_default:
            return queue
    if not queues:
        raise ValueError("Instance has no attendance queues configured")
    return queues[0]


def resolve_queue_by_slug(queues: Sequence[AttendanceQueue], slug: str | None) -> AttendanceQueue:
    """Resolves the queue slug the AI chose in its `[ESCALAR:conf:slug]` tag. Falls back to the
    default queue when the slug is missing, unknown, or points at an inactive queue - the model
    doesn't always follow the format exactly."""
    if slug:
        for queue in queues:
            if queue.slug == slug and queue.active:
                return queue
    return resolve_default_queue(queues)


def to_escalation_options(queues: Sequence[AttendanceQueue]) -> list[EscalationQueueOption]:
    """Active queues as AI-facing options for `AiAssistProvider.reply`, default queue first so
    it's the one `build_escalation_suffix` points at as the fallback example."""
    active = [queue for queue in queues if queue.active]
    active.sort(key=lambda queue: (not queue.is_default, queue.position))
    return [EscalationQueueOption(slug=queue.slug, name=queue.name, routing_hint=queue.routing_hint) for queue in active]


async def _send_canned_message_and_escalate(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    *,
    message: str,
    queue: AttendanceQueue | None,
    escalation_reason: EscalationReason,
) -> None:
    """Shared by `_handoff_to_human` and `escalate_for_ai_failure`: sends a canned message,
    records it as a SYSTEM-origin outbound message, and pauses+flags the thread. `queue` is
    None only for the defensive "no attendance queue configured at all" edge case (should never
    happen in production - every instance always gets a default queue - but the customer-facing
    message must still go out even if that invariant is somehow violated): the thread is paused
    and flagged as escalated either way, but only actually enters the queue (QUEUED status,
    QueueEvent) when a queue is available to route it into."""
    await send_reply(instance, parsed.sender_number, message, parsed.whatsbotmais_token)
    db.add(
        ConversationMessage(
            instance_id=instance.id,
            sender_number=parsed.sender_number,
            direction=MessageDirection.OUTBOUND,
            kind=MessageKind.TEXT,
            text=message,
            origin=MessageOrigin.SYSTEM,
        )
    )
    thread.ai_paused = True
    thread.escalated = True
    if queue is not None:
        await enqueue_thread(db, thread, escalation_reason=escalation_reason, queue_id=queue.id)
    await db.commit()


async def _handoff_to_human(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    queues: Sequence[AttendanceQueue],
    matched_text: str,
) -> None:
    """Sends the canned handoff acknowledgement, records it, and pauses+flags the thread as
    needing human attention. No AI call involved - safe to run even without a configured
    provider or remaining daily budget. Routes into a queue via a deterministic keyword match
    against `matched_text` (`match_queue_by_keywords`), falling back to the instance's default
    queue."""
    queue = match_queue_by_keywords(queues, matched_text) or resolve_default_queue(queues)
    await _send_canned_message_and_escalate(
        db, instance, parsed, thread,
        message=HANDOFF_ACK_MESSAGE, queue=queue, escalation_reason=EscalationReason.CUSTOMER_REQUEST,
    )
    logger.info(
        "Instance %s: customer requested human handoff for %s, routed to queue '%s'",
        instance.id,
        parsed.sender_number,
        queue.slug,
    )


async def escalate_for_ai_failure(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    queues: Sequence[AttendanceQueue],
) -> None:
    """Graceful-degradation fallback for `app.services.ai_reply.try_reply`: called when the AI
    provider call itself fails (timeout, rate limit, 5xx, malformed response) for a message no
    earlier deterministic step (keyword handoff, chatbot tree) already answered. The customer
    must never be left without any reply just because the provider had a bad moment, so this
    always sends `AI_FAILURE_MESSAGE` and pauses the AI on this thread (so it stops retrying the
    same failing call on every follow-up message) - routing into the default queue is
    best-effort on top of that guarantee, not a precondition for it. Tagged
    `EscalationReason.AI_FAILURE` (distinct from `CUSTOMER_REQUEST`/`AI_UNCERTAIN`) so the queue
    UI and analytics can tell "the provider broke" apart from a normal escalation."""
    try:
        queue = resolve_default_queue(queues)
    except ValueError:
        queue = None
        logger.error(
            "Instance %s has no attendance queue configured; AI failure fallback for %s sent "
            "without queue routing",
            instance.id,
            parsed.sender_number,
        )
    await _send_canned_message_and_escalate(
        db, instance, parsed, thread,
        message=AI_FAILURE_MESSAGE, queue=queue, escalation_reason=EscalationReason.AI_FAILURE,
    )
    logger.warning(
        "Instance %s: AI provider failed for %s, sent fallback message and escalated%s",
        instance.id,
        parsed.sender_number,
        f" to queue '{queue.slug}'" if queue is not None else " (no queue available)",
    )


async def handoff_if_requested(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    queues: Sequence[AttendanceQueue],
    text: str,
) -> bool:
    """Checks whether `text` explicitly asks for a human handoff (`customer_requests_handoff`)
    and, if so, hands off via `_handoff_to_human` and returns True. Shared by `try_handoff`
    below (checked against the raw inbound text/caption) and `app.services.ai_reply.try_reply`
    (checked against the transcribed text of an audio message, only available after
    transcription)."""
    if not customer_requests_handoff(text):
        return False
    await _handoff_to_human(db, instance, parsed, thread, queues, matched_text=text)
    return True


async def try_handoff(
    db: AsyncSession,
    instance: Instance,
    parsed: ParsedInboundMessage,
    thread: ConversationThread,
    queues: Sequence[AttendanceQueue],
) -> bool:
    """First step of `app.api.v1.routers.webhooks._maybe_auto_reply`'s auto-reply pipeline: a
    customer explicitly asking for a human should hand off even if the AI isn't configured, the
    daily budget is spent, or the chatbot is enabled - checked before either of those paths.
    Audio messages are excluded here since there's nothing to match yet;
    `app.services.ai_reply.try_reply` re-checks them after transcription. Returns True if a
    handoff was triggered (nothing further should run for this message)."""
    if parsed.media_kind == "audio":
        return False
    return await handoff_if_requested(db, instance, parsed, thread, queues, parsed.text)


async def reopen_if_resolved(db: AsyncSession, thread: ConversationThread, queues: Sequence[AttendanceQueue]) -> None:
    """Called on every inbound message regardless of `ai_paused`: a RESOLVED thread whose AI is
    still paused (resolving doesn't hand control back to the AI - only the separate resume
    endpoint does) would otherwise sit invisible to both the AI and the queue once the customer
    writes again. Keeps the thread's existing `queue_id` (same team keeps continuity) unless it
    was cleared by a queue deletion, in which case it falls back to the default queue."""
    if thread.queue_status != QueueStatus.RESOLVED:
        return
    # escalation_reason is always set by the time a thread reaches RESOLVED (it only gets there
    # via QUEUED); the fallback is just to satisfy the type checker.
    queue_id = thread.queue_id or resolve_default_queue(queues).id
    await enqueue_thread(
        db,
        thread,
        escalation_reason=thread.escalation_reason or EscalationReason.CUSTOMER_REQUEST,
        queue_id=queue_id,
    )


async def claim(db: AsyncSession, thread: ConversationThread, agent_user_id: uuid.UUID) -> None:
    """QUEUED/ON_HOLD -> IN_PROGRESS, assigned to `agent_user_id`. Also used to implicitly claim
    when a human sends a manual reply straight from the conversation view without going through
    the queue UI first - whoever is actually typing to the customer becomes the owner."""
    thread.queue_status = QueueStatus.IN_PROGRESS
    thread.assigned_agent_id = agent_user_id
    thread.assigned_at = datetime.now(timezone.utc)
    db.add(QueueEvent(thread_id=thread.id, event_type=QueueEventType.CLAIMED, agent_user_id=agent_user_id))


def hold(thread: ConversationThread) -> None:
    thread.queue_status = QueueStatus.ON_HOLD


def unhold(thread: ConversationThread) -> None:
    thread.queue_status = QueueStatus.IN_PROGRESS


def resolve(db: AsyncSession, thread: ConversationThread, agent_user_id: uuid.UUID) -> None:
    thread.queue_status = QueueStatus.RESOLVED
    thread.resolved_at = datetime.now(timezone.utc)
    db.add(QueueEvent(thread_id=thread.id, event_type=QueueEventType.RESOLVED, agent_user_id=agent_user_id))


def reset(thread: ConversationThread) -> None:
    """Full reset back to NONE - used by `resume_conversation` when a human hands control back
    to the AI, so a stale "assigned to X" / QUEUED card doesn't linger in the queue panel."""
    thread.queue_status = QueueStatus.NONE
    thread.escalation_reason = None
    thread.ai_confidence = None
    thread.assigned_agent_id = None
    thread.queue_id = None
    thread.queued_at = None
    thread.assigned_at = None
    thread.resolved_at = None


async def get_or_create_agent_profile(db: AsyncSession, instance_id: uuid.UUID, user_id: uuid.UUID) -> AgentProfile:
    profile = await db.scalar(
        select(AgentProfile).where(AgentProfile.instance_id == instance_id, AgentProfile.user_id == user_id)
    )
    if profile is None:
        profile = AgentProfile(instance_id=instance_id, user_id=user_id, status=AgentAvailability.OFFLINE)
        db.add(profile)
        await db.flush()
    return profile
