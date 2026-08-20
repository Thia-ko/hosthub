import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class QueueBasePriority(str, enum.Enum):
    """Floor priority for every item routed into this queue - combined with the time-based
    escalation in `app.services.queue.compute_priority` (whichever is higher wins), so a queue
    configured as URGENT never shows as "normal" just because a card is fresh."""

    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AttendanceQueue(Base):
    """A named team/topic queue an instance's admin configures (e.g. "Financeiro", "Suporte
    Tecnico", "Vendas") to sort escalated conversations before a human ever sees them.

    Routing into a queue happens at enqueue time (`app.services.queue.enqueue_thread`), via one
    of two deterministic-first mechanisms depending on which trigger fired
    (`app.services.escalation`):
    - Customer explicitly asks for a human (keyword match, no AI call): matched against this
      queue's own `keywords` (comma-separated substrings), same cheap mechanism as the existing
      handoff-keyword check - keeps working even with no AI provider configured.
    - The AI decides to escalate: `routing_hint` (free text) is injected into the escalation
      instruction sent to the model, which is asked to pick a queue slug alongside its
      confidence (see `app.services.escalation.build_escalation_suffix`).
    Either path falls back to the instance's `is_default` queue when nothing matches.

    Every instance always has exactly one `is_default=True` queue (created alongside the
    instance, see `app.api.v1.routers.instances.create_instance`, and backfilled for
    pre-existing instances by migration 0026) - it can't be deleted or deactivated, so routing
    always has somewhere to land.
    """

    __tablename__ = "attendance_queues"
    __table_args__ = (UniqueConstraint("instance_id", "slug", name="uq_attendance_queues_instance_slug"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # Stable identifier referenced in the AI's [ESCALAR:confidence:slug] tag and never changed
    # after creation, even if `name` is edited later - generated once from `name` via
    # `app.core.slug.slugify` at creation time.
    slug: Mapped[str] = mapped_column(String, nullable=False)
    # Free text fed into the AI's escalation instruction describing when this queue applies
    # (e.g. "Duvidas sobre cobranca, reembolso, nota fiscal") - the "quando a IA deve encaminhar
    # para esta fila" configuration.
    routing_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Comma-separated phrases matched (substring, case-insensitive) against the customer's
    # message on the keyword-triggered handoff path, which never calls the AI.
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_priority: Mapped[QueueBasePriority] = mapped_column(
        Enum(QueueBasePriority, name="queue_base_priority"), nullable=False, default=QueueBasePriority.NORMAL
    )
    # Hex color for the Kanban card accent/badge - a fixed frontend swatch picker, not a free
    # color input.
    color: Mapped[str] = mapped_column(String, nullable=False, default="#64748b")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
