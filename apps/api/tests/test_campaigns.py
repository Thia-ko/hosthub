"""Integration tests for the campaign 24h WhatsApp window rule (app.services.campaigns).

WhatsApp/Meta requires a pre-approved template to message a customer outside the 24h window
since their last inbound message; HostHub has no template management, so `_process_recipient`
must skip anyone outside that window rather than risk the number getting flagged/blocked - see
WINDOW in app.services.campaigns and campaigns-panel.tsx on the frontend side.

These hit the real database (async_session) rather than mocking it: the window check is a SQL
query (latest inbound ConversationMessage vs a cutoff), so the thing actually worth verifying is
that query's behavior, not a mock's. Only the outbound WhatsApp send (app.services.whatsapp_channel)
is monkeypatched - that's the one call that would otherwise hit the real WhatsBotMais API.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.db.session import async_session
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_recipient import CampaignRecipient, CampaignRecipientStatus
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind
from app.models.instance import Instance, InstanceStatus
from app.models.user import User, UserRole
from app.services import campaigns
from app.services.whatsapp_channel import WhatsAppChannelError


@pytest.fixture
async def instance():
    """A real, persisted Instance owned by a real User - _process_recipient loads both by id
    from the DB, so in-memory-only objects won't do. Everything created here is deleted in the
    teardown, regardless of test outcome."""
    unique = uuid.uuid4().hex[:8]
    async with async_session() as db:
        owner = User(
            email=f"owner-{unique}@example.com",
            password_hash="x",
            role=UserRole.CLIENT,
            full_name="Owner",
        )
        db.add(owner)
        await db.flush()
        inst = Instance(
            name=f"Instance {unique}",
            slug=f"instance-{unique}",
            owner_user_id=owner.id,
            created_by_admin_id=owner.id,
            status=InstanceStatus.ACTIVE,
            whatsapp_instance_name="evo-connection",  # so send_reply has a channel to pick
        )
        db.add(inst)
        await db.commit()
        await db.refresh(inst)
        instance_id = inst.id
        owner_id = owner.id

    yield inst

    async with async_session() as db:
        await db.execute(CampaignRecipient.__table__.delete().where(CampaignRecipient.campaign_id.in_(
            select(Campaign.id).where(Campaign.instance_id == instance_id)
        )))
        await db.execute(Campaign.__table__.delete().where(Campaign.instance_id == instance_id))
        await db.execute(
            ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == instance_id)
        )
        from app.models.conversation_thread import ConversationThread

        await db.execute(ConversationThread.__table__.delete().where(ConversationThread.instance_id == instance_id))
        await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
        await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


async def _make_campaign(instance: Instance, message: str = "Promocao especial!") -> Campaign:
    async with async_session() as db:
        campaign = Campaign(
            instance_id=instance.id,
            name="Campanha de teste",
            message=message,
            created_by_user_id=instance.owner_user_id,
        )
        db.add(campaign)
        await db.commit()
        await db.refresh(campaign)
        return campaign


async def _inbound_message(instance: Instance, sender_number: str, age: timedelta) -> None:
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


async def _reload_campaign(campaign_id: uuid.UUID) -> Campaign:
    async with async_session() as db:
        return await db.get(Campaign, campaign_id)


async def _recipient_status(campaign_id: uuid.UUID, sender_number: str) -> CampaignRecipientStatus:
    async with async_session() as db:
        recipient = await db.scalar(
            select(CampaignRecipient).where(
                CampaignRecipient.campaign_id == campaign_id, CampaignRecipient.sender_number == sender_number
            )
        )
        assert recipient is not None, f"no CampaignRecipient row created for {sender_number}"
        return recipient.status


async def test_recipient_outside_the_24h_window_is_skipped_and_never_sent(instance, monkeypatch):
    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("send_reply must not be called for a recipient outside the window")

    monkeypatch.setattr(campaigns, "send_reply", _fail_if_called)

    sender = "5511999990001"
    await _inbound_message(instance, sender, age=timedelta(hours=25))
    campaign = await _make_campaign(instance)
    cutoff = datetime.now(timezone.utc) - campaigns.WINDOW

    await campaigns._process_recipient(campaign.id, instance.id, sender, cutoff)

    assert await _recipient_status(campaign.id, sender) == CampaignRecipientStatus.SKIPPED_WINDOW
    reloaded = await _reload_campaign(campaign.id)
    assert reloaded.skipped_count == 1
    assert reloaded.sent_count == 0


async def test_recipient_just_outside_the_window_boundary_is_skipped(instance, monkeypatch):
    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("send_reply must not be called just outside the window")

    monkeypatch.setattr(campaigns, "send_reply", _fail_if_called)

    sender = "5511999990002"
    await _inbound_message(instance, sender, age=campaigns.WINDOW + timedelta(minutes=1))
    campaign = await _make_campaign(instance)
    cutoff = datetime.now(timezone.utc) - campaigns.WINDOW

    await campaigns._process_recipient(campaign.id, instance.id, sender, cutoff)

    assert await _recipient_status(campaign.id, sender) == CampaignRecipientStatus.SKIPPED_WINDOW


async def test_recipient_inside_the_window_is_sent_and_logged_as_outbound(instance, monkeypatch):
    sent_calls = []

    async def _fake_send_reply(inst, sender_number, text, whatsbotmais_token):
        sent_calls.append((sender_number, text))

    monkeypatch.setattr(campaigns, "send_reply", _fake_send_reply)

    sender = "5511999990003"
    await _inbound_message(instance, sender, age=timedelta(hours=1))
    campaign = await _make_campaign(instance, message="Promocao dentro da janela")
    cutoff = datetime.now(timezone.utc) - campaigns.WINDOW

    await campaigns._process_recipient(campaign.id, instance.id, sender, cutoff)

    assert sent_calls == [(sender, "Promocao dentro da janela")]
    assert await _recipient_status(campaign.id, sender) == CampaignRecipientStatus.SENT
    reloaded = await _reload_campaign(campaign.id)
    assert reloaded.sent_count == 1
    assert reloaded.skipped_count == 0

    async with async_session() as db:
        outbound = await db.scalar(
            select(ConversationMessage).where(
                ConversationMessage.instance_id == instance.id,
                ConversationMessage.sender_number == sender,
                ConversationMessage.direction == MessageDirection.OUTBOUND,
            )
        )
        assert outbound is not None
        assert outbound.text == "Promocao dentro da janela"


async def test_channel_failure_inside_the_window_is_recorded_as_failed_not_sent(instance, monkeypatch):
    async def _boom(*args, **kwargs):
        raise WhatsAppChannelError("canal indisponivel")

    monkeypatch.setattr(campaigns, "send_reply", _boom)

    sender = "5511999990004"
    await _inbound_message(instance, sender, age=timedelta(hours=1))
    campaign = await _make_campaign(instance)
    cutoff = datetime.now(timezone.utc) - campaigns.WINDOW

    await campaigns._process_recipient(campaign.id, instance.id, sender, cutoff)

    assert await _recipient_status(campaign.id, sender) == CampaignRecipientStatus.FAILED
    reloaded = await _reload_campaign(campaign.id)
    assert reloaded.failed_count == 1
    assert reloaded.sent_count == 0


async def test_recipient_who_never_messaged_is_skipped(instance, monkeypatch):
    """No inbound ConversationMessage at all (e.g. data inconsistency) must fail closed - skip,
    not send - same as a stale conversation."""

    async def _fail_if_called(*args, **kwargs):
        raise AssertionError("send_reply must not be called with no inbound history")

    monkeypatch.setattr(campaigns, "send_reply", _fail_if_called)

    sender = "5511999990005"
    campaign = await _make_campaign(instance)
    cutoff = datetime.now(timezone.utc) - campaigns.WINDOW

    await campaigns._process_recipient(campaign.id, instance.id, sender, cutoff)

    assert await _recipient_status(campaign.id, sender) == CampaignRecipientStatus.SKIPPED_WINDOW
