import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OutboundWebhookSubscription(Base):
    """A URL (n8n/Zapier/CRM) the instance owner wants notified when platform events happen.
    `events` is a JSON-encoded array of event names from app.services.outbound_webhooks.EVENTS -
    same storage convention as AttendantPattern.examples. Delivery is best-effort, single
    attempt, fire-and-forget: see app.services.outbound_webhooks.dispatch_event."""

    __tablename__ = "outbound_webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    events: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
