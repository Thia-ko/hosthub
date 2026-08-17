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
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind
from app.models.instance import Instance, InstanceStatus
from app.models.user import User, UserRole
from app.services.dashboard_stats import get_daily_message_counts, get_daily_token_usage


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
    await _inbound_message(instance, timedelta(hours=1))  # today
    await _inbound_message(instance, timedelta(hours=2))  # today, same bucket
    await _inbound_message(instance, timedelta(days=2))  # 2 days ago
    await _inbound_message(instance, timedelta(days=10))  # outside the 7-day window
    await _outbound_message(instance, timedelta(hours=1))  # our own reply - must not count

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
    await _ai_assist_request(instance, total_tokens=150, age=timedelta(hours=1))
    await _ai_assist_request(instance, total_tokens=50, age=timedelta(hours=2))
    await _ai_assist_request(instance, total_tokens=999, age=timedelta(days=10))  # out of window

    async with async_session() as db:
        result = await get_daily_token_usage(db, instance_id=instance.id, days=7)

    today = datetime.now(timezone.utc).date()
    assert dict(result)[today] == 200
    assert sum(c for _d, c in result) == 200
