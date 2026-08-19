import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ChatbotNode(Base):
    """One node in an instance's deterministic (non-AI) reply tree - see app.services.chatbot
    and app.services.plans.InstanceFeatures.chatbot_enabled. `parent_id` null marks the single
    root (the greeting + main menu, enforced unique per instance by a partial DB index); every
    other node is a menu option reachable from its parent. `keywords` (JSON-encoded array, same
    storage convention as OutboundWebhookSubscription.events) are extra trigger phrases besides
    the node's numbered position within its parent's menu. A node with children behaves as a
    sub-menu; a node with none is a leaf answer. Deleting a node cascades to its whole subtree
    (ON DELETE CASCADE) and clears any ConversationThread parked on a node inside it (ON DELETE
    SET NULL, restarting that customer's chatbot session from the root on their next message)."""

    __tablename__ = "chatbot_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chatbot_nodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    label: Mapped[str] = mapped_column(String, nullable=False)
    keywords: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
