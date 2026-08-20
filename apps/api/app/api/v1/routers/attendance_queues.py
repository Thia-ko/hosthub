import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.core.slug import slugify
from app.db.session import get_db
from app.models.attendance_queue import AttendanceQueue
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance
from app.schemas.attendance_queue import (
    AttendanceQueueCreateRequest,
    AttendanceQueueOut,
    AttendanceQueueReorderRequest,
    AttendanceQueueUpdateRequest,
)

router = APIRouter(prefix="/instances/{instance_id}/attendance-queues", tags=["attendance-queues"])


async def _unique_slug(db: AsyncSession, instance_id: uuid.UUID, name: str) -> str:
    base = slugify(name)
    slug = base
    suffix = 2
    while (
        await db.scalar(
            select(AttendanceQueue).where(AttendanceQueue.instance_id == instance_id, AttendanceQueue.slug == slug)
        )
    ) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


async def _get_queue_or_404(db: AsyncSession, instance: Instance, queue_id: uuid.UUID) -> AttendanceQueue:
    queue = await db.scalar(
        select(AttendanceQueue).where(AttendanceQueue.id == queue_id, AttendanceQueue.instance_id == instance.id)
    )
    if queue is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fila nao encontrada")
    return queue


@router.get("", response_model=list[AttendanceQueueOut])
async def list_attendance_queues(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[AttendanceQueue]:
    result = await db.execute(
        select(AttendanceQueue)
        .where(AttendanceQueue.instance_id == instance.id)
        .order_by(AttendanceQueue.position.asc(), AttendanceQueue.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("", response_model=AttendanceQueueOut)
async def create_attendance_queue(
    payload: AttendanceQueueCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> AttendanceQueue:
    max_position = await db.scalar(
        select(AttendanceQueue.position)
        .where(AttendanceQueue.instance_id == instance.id)
        .order_by(AttendanceQueue.position.desc())
        .limit(1)
    )
    queue = AttendanceQueue(
        instance_id=instance.id,
        name=payload.name,
        slug=await _unique_slug(db, instance.id, payload.name),
        routing_hint=payload.routing_hint,
        keywords=payload.keywords,
        base_priority=payload.base_priority,
        color=payload.color,
        position=(max_position or 0) + 1,
    )
    db.add(queue)
    await db.commit()
    await db.refresh(queue)
    return queue


@router.patch("/{queue_id}", response_model=AttendanceQueueOut)
async def update_attendance_queue(
    queue_id: uuid.UUID,
    payload: AttendanceQueueUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> AttendanceQueue:
    queue = await _get_queue_or_404(db, instance, queue_id)
    if queue.is_default and payload.active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A fila padrao nao pode ser desativada"
        )
    if payload.name is not None:
        queue.name = payload.name
    if payload.routing_hint is not None:
        queue.routing_hint = payload.routing_hint or None
    if payload.keywords is not None:
        queue.keywords = payload.keywords or None
    if payload.base_priority is not None:
        queue.base_priority = payload.base_priority
    if payload.color is not None:
        queue.color = payload.color
    if payload.active is not None:
        queue.active = payload.active
    await db.commit()
    await db.refresh(queue)
    return queue


@router.put("/reorder", response_model=list[AttendanceQueueOut])
async def reorder_attendance_queues(
    payload: AttendanceQueueReorderRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> list[AttendanceQueue]:
    result = await db.execute(select(AttendanceQueue).where(AttendanceQueue.instance_id == instance.id))
    queues_by_id = {queue.id: queue for queue in result.scalars()}
    if set(payload.ordered_ids) != set(queues_by_id.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A lista precisa conter exatamente as filas existentes"
        )
    for position, queue_id in enumerate(payload.ordered_ids):
        queues_by_id[queue_id].position = position
    await db.commit()
    return sorted(queues_by_id.values(), key=lambda q: q.position)


@router.delete("/{queue_id}", response_model=dict)
async def delete_attendance_queue(
    queue_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    queue = await _get_queue_or_404(db, instance, queue_id)
    if queue.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A fila padrao nao pode ser excluida")

    default_queue = await db.scalar(
        select(AttendanceQueue).where(AttendanceQueue.instance_id == instance.id, AttendanceQueue.is_default.is_(True))
    )
    # Re-home any thread still pointed at this queue (active or already resolved/history) to the
    # default queue instead of leaving them dangling - the FK is ON DELETE SET NULL so this isn't
    # strictly required for integrity, but a silently NULL queue would be confusing in the UI.
    if default_queue is not None:
        await db.execute(
            ConversationThread.__table__.update()
            .where(ConversationThread.queue_id == queue.id)
            .values(queue_id=default_queue.id)
        )
    await db.delete(queue)
    await db.commit()
    return {"deleted": True}
