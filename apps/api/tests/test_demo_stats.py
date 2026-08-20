"""Integration tests for the public platform stats endpoint (app.api.v1.routers.demo:get_public_stats),
which powers the landing page's live ticker. The underlying aggregation math (AI-resolved vs.
human-touched threads, escalation exclusion, day windowing) is already covered thoroughly by
test_dashboard_stats.py against app.services.dashboard_stats.get_resolution_stats - these tests
only check that the router wraps it correctly: unscoped (platform-wide), no auth required, and
the response shape matches what the schema promises.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.api.v1.routers.demo import get_public_stats
from app.db.session import async_session
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.instance import Instance, InstanceStatus
from app.models.user import User, UserRole


async def _inbound_from(instance: Instance, sender_number: str, age: timedelta) -> None:
    async with async_session() as db:
        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number=sender_number,
                direction=MessageDirection.INBOUND,
                kind=MessageKind.TEXT,
                text="Oi",
                created_at=datetime.now(timezone.utc) - age,
            )
        )
        await db.commit()


async def _outbound_from(instance: Instance, sender_number: str, origin: MessageOrigin, age: timedelta) -> None:
    async with async_session() as db:
        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number=sender_number,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT,
                text="Resposta",
                origin=origin,
                created_at=datetime.now(timezone.utc) - age,
            )
        )
        await db.commit()


async def test_public_stats_requires_no_auth_and_reports_seven_day_window():
    async with async_session() as db:
        stats = await get_public_stats(db)
    assert stats.window_days == 7
    assert stats.ai_resolved_threads >= 0
    assert stats.estimated_hours_saved >= 0.0


async def test_public_stats_is_platform_wide_not_scoped_to_one_instance():
    unique = uuid.uuid4().hex[:8]
    async with async_session() as db:
        owner = User(email=f"owner-{unique}@example.com", password_hash="x", role=UserRole.CLIENT, full_name="Owner")
        db.add(owner)
        await db.flush()
        inst = Instance(
            name=f"Instance {unique}",
            slug=f"instance-{unique}",
            owner_user_id=owner.id,
            created_by_admin_id=owner.id,
            status=InstanceStatus.ACTIVE,
        )
        db.add(inst)
        await db.commit()
        await db.refresh(inst)

    try:
        async with async_session() as db:
            baseline = await get_public_stats(db)

        sender = f"55119{uuid.uuid4().int % 10**8:08d}"
        await _inbound_from(inst, sender, timedelta(hours=1))
        await _outbound_from(inst, sender, MessageOrigin.AI, timedelta(minutes=59))

        async with async_session() as db:
            after = await get_public_stats(db)

        # A new AI-resolved thread on a brand-new instance must show up in the unscoped total -
        # if the router accidentally filtered by some default instance, this would stay flat.
        assert after.ai_resolved_threads == baseline.ai_resolved_threads + 1
    finally:
        async with async_session() as db:
            await db.execute(ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == inst.id))
            await db.execute(Instance.__table__.delete().where(Instance.id == inst.id))
            await db.execute(User.__table__.delete().where(User.id == owner.id))
            await db.commit()
