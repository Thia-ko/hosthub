"""Integration tests for app.services.dashboard_stats (the 7-day rollups backing the dashboard
sparklines). Hits the real database like test_campaigns.py - the thing worth verifying is the
day-bucketing SQL (correct date, zero-filled gaps, INBOUND-only, correct instance scoping), not a
mock's behavior.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.db.session import async_session
from app.models.ai_assist_request import AiAssistRequest
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance, InstanceStatus
from app.models.user import User, UserRole
from app.services.dashboard_stats import (
    AVG_MANUAL_HANDLE_MINUTES,
    get_daily_message_counts,
    get_daily_token_usage,
    get_resolution_stats,
)


@pytest.fixture
async def instance():
    unique = uuid.uuid4().hex[:8]
    async with async_session() as db:
        owner = User(
            email=f"owner-{unique}@example.com", password_hash="x", role=UserRole.CLIENT, full_name="Owner"
        )
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
        instance_id, owner_id = inst.id, owner.id

    yield inst

    async with async_session() as db:
        await db.execute(ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == instance_id))
        await db.execute(ConversationThread.__table__.delete().where(ConversationThread.instance_id == instance_id))
        await db.execute(AiAssistRequest.__table__.delete().where(AiAssistRequest.instance_id == instance_id))
        await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
        await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


async def _inbound_message(instance: Instance, age: timedelta) -> None:
    async with async_session() as db:
        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number="5511999999999",
                direction=MessageDirection.INBOUND,
                kind=MessageKind.TEXT,
                text="Oi",
                created_at=datetime.now(timezone.utc) - age,
            )
        )
        await db.commit()


async def _outbound_message(instance: Instance, age: timedelta) -> None:
    async with async_session() as db:
        db.add(
            ConversationMessage(
                instance_id=instance.id,
                sender_number="5511999999999",
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT,
                text="Resposta",
                created_at=datetime.now(timezone.utc) - age,
            )
        )
        await db.commit()


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


async def _outbound_from(
    instance: Instance, sender_number: str, origin: MessageOrigin, age: timedelta
) -> None:
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


async def _ai_assist_request(instance: Instance, total_tokens: int, age: timedelta) -> None:
    async with async_session() as db:
        db.add(
            AiAssistRequest(
                instance_id=instance.id,
                user_id=instance.owner_user_id,
                instruction="ajuste o tom",
                total_tokens=total_tokens,
                created_at=datetime.now(timezone.utc) - age,
            )
        )
        await db.commit()


async def test_empty_instance_returns_seven_zero_filled_days(instance):
    async with async_session() as db:
        result = await get_daily_message_counts(db, instance_id=instance.id, days=7)
    assert len(result) == 7
    assert all(count == 0 for _day, count in result)
    assert result[-1][0] == datetime.now(timezone.utc).date()


async def test_buckets_by_day_excludes_outbound_and_out_of_range(instance):
    await _inbound_message(instance, timedelta(minutes=2))  # today
    await _inbound_message(instance, timedelta(minutes=1))  # today, same bucket
    await _inbound_message(instance, timedelta(days=2))  # 2 days ago
    await _inbound_message(instance, timedelta(days=10))  # outside the 7-day window
    await _outbound_message(instance, timedelta(minutes=1))  # our own reply - must not count

    async with async_session() as db:
        result = await get_daily_message_counts(db, instance_id=instance.id, days=7)

    today = datetime.now(timezone.utc).date()
    counts_by_date = dict(result)
    assert counts_by_date[today] == 2
    assert counts_by_date[today - timedelta(days=2)] == 1
    assert sum(c for _d, c in result) == 3  # the 10-days-ago message never enters the window


async def test_message_counts_are_scoped_to_the_instance(instance):
    other_unique = uuid.uuid4().hex[:8]
    async with async_session() as db:
        other_owner = User(
            email=f"owner-{other_unique}@example.com", password_hash="x", role=UserRole.CLIENT, full_name="Other"
        )
        db.add(other_owner)
        await db.flush()
        other_instance = Instance(
            name=f"Other {other_unique}",
            slug=f"other-{other_unique}",
            owner_user_id=other_owner.id,
            created_by_admin_id=other_owner.id,
            status=InstanceStatus.ACTIVE,
        )
        db.add(other_instance)
        await db.commit()
        await db.refresh(other_instance)

    try:
        await _inbound_message(instance, timedelta(hours=1))
        await _inbound_message(other_instance, timedelta(hours=1))

        async with async_session() as db:
            scoped = await get_daily_message_counts(db, instance_id=instance.id, days=7)

        today = datetime.now(timezone.utc).date()
        assert dict(scoped)[today] == 1  # the other instance's message must not leak in
    finally:
        async with async_session() as db:
            await db.execute(
                ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == other_instance.id)
            )
            await db.execute(Instance.__table__.delete().where(Instance.id == other_instance.id))
            await db.execute(User.__table__.delete().where(User.id == other_instance.owner_user_id))
            await db.commit()


async def test_platform_wide_count_includes_every_instance(instance):
    """instance_id=None (used by the admin overview) must not filter by instance."""
    async with async_session() as db:
        baseline = dict(await get_daily_message_counts(db, days=7))
    today = datetime.now(timezone.utc).date()

    await _inbound_message(instance, timedelta(hours=1))

    async with async_session() as db:
        after = dict(await get_daily_message_counts(db, days=7))

    assert after[today] == baseline[today] + 1


async def test_token_usage_buckets_by_day_and_scopes_to_instance(instance):
    await _ai_assist_request(instance, total_tokens=150, age=timedelta(minutes=2))
    await _ai_assist_request(instance, total_tokens=50, age=timedelta(minutes=1))
    await _ai_assist_request(instance, total_tokens=999, age=timedelta(days=10))  # out of window

    async with async_session() as db:
        result = await get_daily_token_usage(db, instance_id=instance.id, days=7)

    today = datetime.now(timezone.utc).date()
    assert dict(result)[today] == 200
    assert sum(c for _d, c in result) == 200


async def test_resolution_stats_empty_instance_returns_none_rate(instance):
    async with async_session() as db:
        stats = await get_resolution_stats(db, instance_id=instance.id, days=7)
    assert stats.threads_with_activity == 0
    assert stats.ai_resolved_threads == 0
    assert stats.resolution_rate_pct is None
    assert stats.estimated_hours_saved == 0.0


async def test_resolution_stats_splits_ai_resolved_from_human_touched(instance):
    await _inbound_from(instance, "5511900000001", timedelta(hours=1))
    await _outbound_from(instance, "5511900000001", MessageOrigin.AI, timedelta(minutes=59))

    await _inbound_from(instance, "5511900000002", timedelta(hours=1))
    await _outbound_from(instance, "5511900000002", MessageOrigin.HUMAN, timedelta(minutes=59))

    async with async_session() as db:
        stats = await get_resolution_stats(db, instance_id=instance.id, days=7)

    assert stats.threads_with_activity == 2
    assert stats.ai_resolved_threads == 1
    assert stats.resolution_rate_pct == 50.0
    assert stats.estimated_hours_saved == round(1 * AVG_MANUAL_HANDLE_MINUTES / 60, 1)


async def test_resolution_stats_system_origin_still_counts_as_ai_resolved(instance):
    await _inbound_from(instance, "5511900000003", timedelta(hours=1))
    await _outbound_from(instance, "5511900000003", MessageOrigin.SYSTEM, timedelta(minutes=59))

    async with async_session() as db:
        stats = await get_resolution_stats(db, instance_id=instance.id, days=7)

    assert stats.threads_with_activity == 1
    assert stats.ai_resolved_threads == 1
    assert stats.resolution_rate_pct == 100.0


async def test_resolution_stats_excludes_currently_escalated_thread(instance):
    await _inbound_from(instance, "5511900000004", timedelta(hours=1))
    async with async_session() as db:
        db.add(
            ConversationThread(
                instance_id=instance.id, sender_number="5511900000004", ai_paused=True, escalated=True
            )
        )
        await db.commit()

    async with async_session() as db:
        stats = await get_resolution_stats(db, instance_id=instance.id, days=7)

    assert stats.threads_with_activity == 1
    assert stats.ai_resolved_threads == 0
    assert stats.resolution_rate_pct == 0.0


async def test_resolution_stats_excludes_out_of_window_activity(instance):
    await _inbound_from(instance, "5511900000005", timedelta(days=10))

    async with async_session() as db:
        stats = await get_resolution_stats(db, instance_id=instance.id, days=7)

    assert stats.threads_with_activity == 0


async def test_resolution_stats_scoped_to_instance(instance):
    other_unique = uuid.uuid4().hex[:8]
    async with async_session() as db:
        other_owner = User(
            email=f"owner-{other_unique}@example.com", password_hash="x", role=UserRole.CLIENT, full_name="Other"
        )
        db.add(other_owner)
        await db.flush()
        other_instance = Instance(
            name=f"Other {other_unique}",
            slug=f"other-{other_unique}",
            owner_user_id=other_owner.id,
            created_by_admin_id=other_owner.id,
            status=InstanceStatus.ACTIVE,
        )
        db.add(other_instance)
        await db.commit()
        await db.refresh(other_instance)

    try:
        await _inbound_from(instance, "5511900000006", timedelta(hours=1))
        await _inbound_from(other_instance, "5511900000007", timedelta(hours=1))

        async with async_session() as db:
            scoped = await get_resolution_stats(db, instance_id=instance.id, days=7)
        assert scoped.threads_with_activity == 1
    finally:
        async with async_session() as db:
            await db.execute(
                ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == other_instance.id)
            )
            await db.execute(Instance.__table__.delete().where(Instance.id == other_instance.id))
            await db.execute(User.__table__.delete().where(User.id == other_owner.id))
            await db.commit()
