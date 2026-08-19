import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ApiKey(Base):
    """A machine credential (Bearer token) scoped to a single instance, letting an external
    system (n8n, a client's own backend/dev team) call the public API in
    app.api.v1.routers.external without a human browser session - see app.core.api_key_auth.

    Only `key_hash` (sha256) is ever persisted; the raw secret is generated and shown to the
    caller exactly once, at creation time (app.services.api_keys.generate_api_key), and is
    unrecoverable afterwards. `key_prefix` is the non-secret leading slice of the raw key, kept
    so the UI can help an operator recognize which key is which without re-displaying the
    secret. `scopes` is a JSON-encoded array of permission strings from
    app.services.api_keys.SCOPES - same storage convention as OutboundWebhookSubscription.events.
    Revocation is soft (`active`/`revoked_at`) rather than a hard delete, so an audit trail of
    who had API access and when survives past revocation."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("instances.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    scopes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
