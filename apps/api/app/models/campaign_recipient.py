import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CampaignRecipientStatus(str, enum.Enum):
    SENT = "sent"
    SKIPPED_WINDOW = "skipped_window"
    FAILED = "failed"


class CampaignRecipient(Base):
    """Per-customer outcome of a Campaign send: SENT, SKIPPED_WINDOW (customer's last inbound
    message is older than app.services.campaigns.WINDOW - WhatsApp/Meta requires a
    pre-approved template to message outside it, which HostHub doesn't support, so these are
    skipped rather than risking the number getting flagged), or FAILED (channel error)."""

    __tablename__ = "campaign_recipients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    sender_number: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[CampaignRecipientStatus] = mapped_column(
        Enum(CampaignRecipientStatus, name="campaign_recipient_status"), nullable=False
    )
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
