import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.deps import get_current_user, get_owned_instance
from app.db.session import get_db
from app.models.agent_profile import AgentAvailability, AgentProfile
from app.models.attendance_queue import AttendanceQueue
from app.models.conversation_message import ConversationMessage, MessageDirection
from app.models.conversation_thread import ConversationThread, QueueStatus
from app.models.instance import Instance
from app.models.instance_member import InstanceMember
from app.models.user import User, UserRole
from app.schemas.queue import (
    AgentProfileOut,
    AgentStatusUpdateRequest,
    QueueContextOut,
    QueueItemAgentOut,
    QueueItemOut,
    QueueItemQueueOut,
    QueueReassignRequest,
)
from app.services import queue as queue_service
from app.services.ai_assist_provider import AiAssistProvider, get_ai_assist_provider

router = APIRouter(prefix="/instances/{instance_id}/queue", tags=["queue"])

_INTENT_SUMMARY_PROMPT = (
    "Voce e um assistente que resume conversas de atendimento ao cliente para um atendente humano que "
    "esta assumindo o caso. Leia a transcricao abaixo (Cliente / Atendimento intercalados) e responda "
    'em JSON no formato {"intent": "frase curta em pt-BR descrevendo o que o cliente quer, no maximo '
    '12 palavras"}. Nao invente informacoes que nao estejam na transcricao.'
)


async def _get_thread_or_404(db: AsyncSession, instance: Instance, sender_number: str) -> ConversationThread:
    thread = await db.scalar(
        select(ConversationThread).where(
            ConversationThread.instance_id == instance.id, ConversationThread.sender_number == sender_number
        )
    )
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa nao encontrada")
    return thread


def _require_owner_or_admin(thread: ConversationThread, user: User) -> None:
    if user.role == UserRole.ADMIN:
        return
    if thread.assigned_agent_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Apenas quem assumiu este atendimento pode fazer isso"
        )


@router.get("", response_model=list[QueueItemOut])
async def list_queue(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[QueueItemOut]:
    """Every thread with an active human-queue lane (QUEUED/IN_PROGRESS/ON_HOLD - RESOLVED is
    deliberately excluded, it only reappears via `queue_service.reopen_if_resolved` on the next
    inbound message), oldest QUEUED first. Two follow-up batch queries (latest message per
    sender, assigned agent names) instead of N+1 - the queue is human-scale (dozens, not
    thousands of rows), so a window-function join like `list_conversations` uses would just add
    complexity for no real gain here."""
    threads = list(
        (
            await db.execute(
                select(ConversationThread)
                .where(
                    ConversationThread.instance_id == instance.id,
                    ConversationThread.queue_status.in_(
                        [QueueStatus.QUEUED, QueueStatus.IN_PROGRESS, QueueStatus.ON_HOLD]
                    ),
                )
                .order_by(ConversationThread.queued_at.asc())
            )
        ).scalars()
    )
    if not threads:
        return []

    sender_numbers = [t.sender_number for t in threads]
    agent_ids = {t.assigned_agent_id for t in threads if t.assigned_agent_id is not None}
    row_number = func.row_number().over(
        partition_by=ConversationMessage.sender_number, order_by=ConversationMessage.created_at.desc()
    )
    ranked = (
        select(ConversationMessage, row_number.label("rn"))
        .where(ConversationMessage.instance_id == instance.id, ConversationMessage.sender_number.in_(sender_numbers))
        .subquery()
    )
    latest = aliased(ConversationMessage, ranked)
    latest_rows = (await db.execute(select(latest).where(ranked.c.rn == 1))).scalars().all()
    latest_by_sender = {m.sender_number: m for m in latest_rows}

    agents_by_id: dict[uuid.UUID, User] = {}
    if agent_ids:
        agent_rows = (await db.execute(select(User).where(User.id.in_(agent_ids)))).scalars().all()
        agents_by_id = {u.id: u for u in agent_rows}

    queue_ids = {t.queue_id for t in threads if t.queue_id is not None}
    queues_by_id: dict[uuid.UUID, AttendanceQueue] = {}
    if queue_ids:
        queue_rows = (
            await db.execute(select(AttendanceQueue).where(AttendanceQueue.id.in_(queue_ids)))
        ).scalars().all()
        queues_by_id = {q.id: q for q in queue_rows}

    now = datetime.now(timezone.utc)
    items: list[QueueItemOut] = []
    for thread in threads:
        wait_seconds = (now - thread.queued_at).total_seconds() if thread.queued_at else 0.0
        last_message = latest_by_sender.get(thread.sender_number)
        agent = agents_by_id.get(thread.assigned_agent_id) if thread.assigned_agent_id else None
        queue = queues_by_id.get(thread.queue_id) if thread.queue_id else None
        items.append(
            QueueItemOut(
                sender_number=thread.sender_number,
                queue_status=thread.queue_status,
                escalation_reason=thread.escalation_reason,
                ai_confidence=thread.ai_confidence,
                priority=queue_service.compute_priority(
                    thread.escalation_reason, wait_seconds, queue.base_priority if queue else None
                ),
                sla_risk=queue_service.compute_sla_risk(wait_seconds),
                wait_time_seconds=int(wait_seconds),
                queued_at=thread.queued_at,
                assigned_at=thread.assigned_at,
                resolved_at=thread.resolved_at,
                assigned_agent=QueueItemAgentOut(id=agent.id, full_name=agent.full_name) if agent else None,
                queue=QueueItemQueueOut(id=queue.id, name=queue.name, color=queue.color) if queue else None,
                last_message_preview=last_message.text if last_message else "",
                last_message_at=last_message.created_at if last_message else thread.updated_at,
            )
        )
    return items


@router.post("/{sender_number}/claim", response_model=QueueItemOut)
async def claim_queue_item(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    thread = await _get_thread_or_404(db, instance, sender_number)
    if thread.queue_status not in (QueueStatus.QUEUED, QueueStatus.ON_HOLD):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este atendimento nao esta disponivel para assumir"
        )
    await queue_service.claim(db, thread, user.id)
    await db.commit()
    return await _single_item(db, instance, thread)


@router.post("/{sender_number}/hold", response_model=QueueItemOut)
async def hold_queue_item(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    thread = await _get_thread_or_404(db, instance, sender_number)
    if thread.queue_status != QueueStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este atendimento nao esta em andamento")
    _require_owner_or_admin(thread, user)
    queue_service.hold(thread)
    await db.commit()
    return await _single_item(db, instance, thread)


@router.post("/{sender_number}/unhold", response_model=QueueItemOut)
async def unhold_queue_item(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    thread = await _get_thread_or_404(db, instance, sender_number)
    if thread.queue_status != QueueStatus.ON_HOLD:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este atendimento nao esta em espera")
    _require_owner_or_admin(thread, user)
    queue_service.unhold(thread)
    await db.commit()
    return await _single_item(db, instance, thread)


@router.post("/{sender_number}/resolve", response_model=QueueItemOut)
async def resolve_queue_item(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    thread = await _get_thread_or_404(db, instance, sender_number)
    if thread.queue_status not in (QueueStatus.IN_PROGRESS, QueueStatus.ON_HOLD):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Este atendimento nao esta em andamento ou em espera"
        )
    _require_owner_or_admin(thread, user)
    queue_service.resolve(db, thread, user.id)
    await db.commit()
    return await _single_item(db, instance, thread)


async def _single_item(db: AsyncSession, instance: Instance, thread: ConversationThread) -> QueueItemOut:
    """Re-serializes one thread after a mutation - reuses the same shape as `list_queue` so the
    frontend can patch a single card instead of refetching the whole queue."""
    now = datetime.now(timezone.utc)
    wait_seconds = (now - thread.queued_at).total_seconds() if thread.queued_at else 0.0
    last_message = await db.scalar(
        select(ConversationMessage)
        .where(ConversationMessage.instance_id == instance.id, ConversationMessage.sender_number == thread.sender_number)
        .order_by(ConversationMessage.created_at.desc())
        .limit(1)
    )
    agent = await db.get(User, thread.assigned_agent_id) if thread.assigned_agent_id else None
    queue = await db.get(AttendanceQueue, thread.queue_id) if thread.queue_id else None
    return QueueItemOut(
        sender_number=thread.sender_number,
        queue_status=thread.queue_status,
        escalation_reason=thread.escalation_reason,
        ai_confidence=thread.ai_confidence,
        priority=queue_service.compute_priority(
            thread.escalation_reason, wait_seconds, queue.base_priority if queue else None
        ),
        sla_risk=queue_service.compute_sla_risk(wait_seconds),
        wait_time_seconds=int(wait_seconds),
        queued_at=thread.queued_at,
        assigned_at=thread.assigned_at,
        resolved_at=thread.resolved_at,
        assigned_agent=QueueItemAgentOut(id=agent.id, full_name=agent.full_name) if agent else None,
        queue=QueueItemQueueOut(id=queue.id, name=queue.name, color=queue.color) if queue else None,
        last_message_preview=last_message.text if last_message else "",
        last_message_at=last_message.created_at if last_message else thread.updated_at,
    )


@router.post("/{sender_number}/reassign-queue", response_model=QueueItemOut)
async def reassign_queue_item(
    sender_number: str,
    payload: QueueReassignRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> QueueItemOut:
    """Manual correction for a misrouted card - any active member can move it to a different
    configured queue, whether the routing (AI or keyword match) got it wrong or priorities
    changed. Does not touch `queue_status`/assignment, only which team owns it."""
    thread = await _get_thread_or_404(db, instance, sender_number)
    if thread.queue_status not in (QueueStatus.QUEUED, QueueStatus.IN_PROGRESS, QueueStatus.ON_HOLD):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este atendimento nao esta na fila")
    target = await db.scalar(
        select(AttendanceQueue).where(
            AttendanceQueue.id == payload.queue_id, AttendanceQueue.instance_id == instance.id
        )
    )
    if target is None or not target.active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fila invalida")
    thread.queue_id = target.id
    await db.commit()
    return await _single_item(db, instance, thread)


@router.get("/{sender_number}/context", response_model=QueueContextOut)
async def get_queue_context(
    sender_number: str,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
    provider: AiAssistProvider = Depends(get_ai_assist_provider),
) -> QueueContextOut:
    """Best-effort context card for the agent picking up a handoff: the last 10 messages plus,
    when the AI provider is configured, a one-line intent summary generated on demand (not
    cached - this is only called when an agent opens a queue item, so the extra call is cheap
    relative to the AI replies already being generated on every message)."""
    thread = await _get_thread_or_404(db, instance, sender_number)
    messages = list(
        reversed(
            (
                await db.execute(
                    select(ConversationMessage)
                    .where(
                        ConversationMessage.instance_id == instance.id,
                        ConversationMessage.sender_number == sender_number,
                    )
                    .order_by(ConversationMessage.created_at.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )
    )

    intent_summary: str | None = None
    if messages and provider.is_configured:
        transcript = "\n".join(
            f"{'Cliente' if m.direction == MessageDirection.INBOUND else 'Atendimento'}: {m.text}" for m in messages
        )
        try:
            parsed, _, _ = await provider.extract_json(_INTENT_SUMMARY_PROMPT, transcript)
            candidate = parsed.get("intent") if isinstance(parsed, dict) else None
            intent_summary = candidate.strip() if isinstance(candidate, str) and candidate.strip() else None
        except Exception:  # noqa: BLE001 - the context card must render even if summarization fails
            intent_summary = None

    return QueueContextOut(
        sender_number=sender_number,
        intent_summary=intent_summary,
        escalation_reason=thread.escalation_reason,
        ai_confidence=thread.ai_confidence,
        recent_messages=list(messages),
    )


@router.get("/agents", response_model=list[AgentProfileOut])
async def list_agents(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[AgentProfileOut]:
    """Every member of the instance (owner + members), with their queue availability - OFFLINE
    for anyone who's never toggled it, since `AgentProfile` rows are created lazily."""
    members = (
        await db.execute(
            select(InstanceMember, User)
            .join(User, User.id == InstanceMember.user_id)
            .where(InstanceMember.instance_id == instance.id)
        )
    ).all()
    profiles = {
        p.user_id: p
        for p in (
            await db.execute(select(AgentProfile).where(AgentProfile.instance_id == instance.id))
        ).scalars()
    }
    return [
        AgentProfileOut(
            user_id=user.id,
            full_name=user.full_name,
            status=profiles[user.id].status if user.id in profiles else AgentAvailability.OFFLINE,
        )
        for _member, user in members
    ]


@router.put("/agents/me", response_model=AgentProfileOut)
async def set_my_agent_status(
    payload: AgentStatusUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentProfileOut:
    profile = await queue_service.get_or_create_agent_profile(db, instance.id, user.id)
    profile.status = payload.status
    await db.commit()
    return AgentProfileOut(user_id=user.id, full_name=user.full_name, status=profile.status)
