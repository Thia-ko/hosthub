"""Integration tests for the AI-reply provider-failure fallback: app.services.ai_reply.try_reply
must never leave the customer without any reply when the AI provider call itself fails (timeout,
rate limit/429, provider 5xx, or a malformed response body) - see
app.services.queue.escalate_for_ai_failure. Hits the real database (async_session), same
convention as test_chatbot_tree.py / test_campaigns.py; only the provider's HTTP call
(OpenAiCompatibleProvider.reply) and the outbound WhatsApp send (Evolution API) are monkeypatched,
so no real network call happens either way.
"""

import uuid

import httpx
import pytest
from sqlalchemy import select

from app.api.v1.routers.webhooks import _maybe_auto_reply
from app.core.config import settings
from app.db.session import async_session
from app.models.ai_assist_request import AiAssistRequest
from app.models.attendance_queue import AttendanceQueue
from app.models.conversation_message import ConversationMessage, MessageOrigin
from app.models.instance import Instance, InstanceStatus, Plan
from app.models.conversation_thread import ConversationThread, EscalationReason, QueueStatus
from app.models.prompt_version import PromptVersion, PromptVersionSource
from app.models.queue_event import QueueEvent
from app.models.user import User, UserRole
from app.services import ai_reply
from app.services.ai_assist_provider import OpenAiCompatibleProvider
from app.services.conversation_threads import get_or_create_thread
from app.services.plans import get_features
from app.services.whatsapp_channel import ParsedInboundMessage


@pytest.fixture(autouse=True)
def _ai_settings(monkeypatch):
    """Pin the AI assist API key so provider.is_configured is always true regardless of .env.
    Every test below monkeypatches OpenAiCompatibleProvider.reply directly, so no test ever
    makes it out to a real provider even with a real key configured."""
    monkeypatch.setattr(settings, "AI_ASSIST_API_KEY", "test-key")


@pytest.fixture
async def instance():
    """A real, persisted, AI-enabled Instance (STARTER plan defaults to ai_enabled=True) with a
    saved prompt version and a default attendance queue - everything try_reply needs to run all
    the way to a provider call."""
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
            whatsapp_instance_name="evo-connection",
            plan=Plan.STARTER,
        )
        db.add(inst)
        await db.flush()
        version = PromptVersion(
            instance_id=inst.id,
            version_number=1,
            content="Voce e um assistente de teste para uma padaria.",
            source=PromptVersionSource.MANUAL,
            created_by_user_id=owner.id,
        )
        db.add(version)
        queue = AttendanceQueue(instance_id=inst.id, name="Geral", slug="geral", is_default=True)
        db.add(queue)
        await db.flush()
        inst.current_prompt_version_id = version.id
        await db.commit()
        await db.refresh(inst)
        instance_id = inst.id
        owner_id = owner.id

    yield inst

    async with async_session() as db:
        await db.execute(
            QueueEvent.__table__.delete().where(
                QueueEvent.thread_id.in_(select(ConversationThread.id).where(ConversationThread.instance_id == instance_id))
            )
        )
        await db.execute(ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == instance_id))
        await db.execute(ConversationThread.__table__.delete().where(ConversationThread.instance_id == instance_id))
        # instances.current_prompt_version_id -> prompt_versions.id is a circular FK back to the
        # row about to be deleted below - null it out first to break the cycle.
        await db.execute(
            Instance.__table__.update().where(Instance.id == instance_id).values(current_prompt_version_id=None)
        )
        await db.execute(PromptVersion.__table__.delete().where(PromptVersion.instance_id == instance_id))
        await db.execute(AiAssistRequest.__table__.delete().where(AiAssistRequest.instance_id == instance_id))
        await db.execute(AttendanceQueue.__table__.delete().where(AttendanceQueue.instance_id == instance_id))
        await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
        await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


async def _fresh_thread(instance: Instance, sender_number: str = "5511999999999") -> ConversationThread:
    async with async_session() as db:
        thread = await get_or_create_thread(db, instance.id, sender_number)
        await db.commit()
        await db.refresh(thread)
        return thread


async def _queues(instance: Instance) -> list[AttendanceQueue]:
    async with async_session() as db:
        result = await db.execute(select(AttendanceQueue).where(AttendanceQueue.instance_id == instance.id))
        return list(result.scalars().all())


# --- Simulated provider failures ----------------------------------------------------------------


async def _raise_timeout(self, *args, **kwargs):
    raise httpx.ReadTimeout("provider did not respond in time", request=httpx.Request("POST", "https://ai.example.com/chat/completions"))


async def _raise_rate_limit(self, *args, **kwargs):
    request = httpx.Request("POST", "https://ai.example.com/chat/completions")
    response = httpx.Response(429, request=request, text='{"error": "rate limited"}')
    raise httpx.HTTPStatusError("429 Too Many Requests", request=request, response=response)


async def _raise_server_error(self, *args, **kwargs):
    request = httpx.Request("POST", "https://ai.example.com/chat/completions")
    response = httpx.Response(500, request=request, text="internal server error")
    raise httpx.HTTPStatusError("500 Internal Server Error", request=request, response=response)


async def _raise_malformed_response(self, *args, **kwargs):
    raise KeyError("choices")


async def _fake_reply_ok(self, system_prompt, history, user_message, image_url=None, max_tokens=None, escalation_queues=()):
    return "Bom dia! Abrimos das 8h as 18h.", 42, 8


# --- try_reply: provider failure always yields a fallback reply, never an exception -------------


@pytest.mark.parametrize(
    "broken_reply",
    [_raise_timeout, _raise_rate_limit, _raise_server_error, _raise_malformed_response],
    ids=["timeout", "rate_limit_429", "server_error_500", "malformed_response"],
)
async def test_try_reply_falls_back_to_human_on_every_provider_failure_mode(instance, monkeypatch, broken_reply):
    monkeypatch.setattr(OpenAiCompatibleProvider, "reply", broken_reply)
    sent_calls = []

    async def _fake_send(whatsapp_instance_name, number, text):
        sent_calls.append((number, text))

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    thread = await _fresh_thread(instance)
    queues = await _queues(instance)
    parsed = ParsedInboundMessage(sender_number=thread.sender_number, text="qual o horario de funcionamento?")

    async with async_session() as db:
        db_instance = await db.get(Instance, instance.id)
        db_thread = await db.get(ConversationThread, thread.id)
        handled = await ai_reply.try_reply(db, db_instance, parsed, db_thread, queues, get_features(db_instance))

    # The customer must always get *something* back - never a silent drop.
    assert handled is True
    assert len(sent_calls) == 1
    assert sent_calls[0][0] == thread.sender_number
    assert "instabilidade tecnica" in sent_calls[0][1]

    async with async_session() as db:
        result = await db.execute(
            select(ConversationMessage).where(ConversationMessage.instance_id == instance.id)
        )
        messages = result.scalars().all()
        assert len(messages) == 1
        assert messages[0].origin == MessageOrigin.SYSTEM
        assert messages[0].text == sent_calls[0][1]

        reloaded_thread = await db.get(ConversationThread, thread.id)
        assert reloaded_thread.ai_paused is True
        assert reloaded_thread.escalated is True
        assert reloaded_thread.escalation_reason == EscalationReason.AI_FAILURE
        assert reloaded_thread.queue_status == QueueStatus.QUEUED
        assert reloaded_thread.queue_id == queues[0].id


async def test_try_reply_logs_the_provider_failure_clearly(instance, monkeypatch, caplog):
    monkeypatch.setattr(OpenAiCompatibleProvider, "reply", _raise_timeout)

    async def _fake_send(whatsapp_instance_name, number, text):
        return None

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    thread = await _fresh_thread(instance)
    queues = await _queues(instance)
    parsed = ParsedInboundMessage(sender_number=thread.sender_number, text="oi")

    with caplog.at_level("ERROR", logger="app.services.ai_reply"):
        async with async_session() as db:
            db_instance = await db.get(Instance, instance.id)
            db_thread = await db.get(ConversationThread, thread.id)
            await ai_reply.try_reply(db, db_instance, parsed, db_thread, queues, get_features(db_instance))

    error_records = [r for r in caplog.records if r.levelname == "ERROR" and r.name == "app.services.ai_reply"]
    assert len(error_records) == 1
    assert str(instance.id) in error_records[0].getMessage()
    assert "ReadTimeout" in error_records[0].getMessage()


async def test_try_reply_sends_the_ai_answer_when_the_provider_succeeds(instance, monkeypatch):
    """Control case: the failure path above must not fire on the happy path."""
    monkeypatch.setattr(OpenAiCompatibleProvider, "reply", _fake_reply_ok)
    sent_calls = []

    async def _fake_send(whatsapp_instance_name, number, text):
        sent_calls.append((number, text))

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    thread = await _fresh_thread(instance)
    queues = await _queues(instance)
    parsed = ParsedInboundMessage(sender_number=thread.sender_number, text="qual o horario?")

    async with async_session() as db:
        db_instance = await db.get(Instance, instance.id)
        db_thread = await db.get(ConversationThread, thread.id)
        handled = await ai_reply.try_reply(db, db_instance, parsed, db_thread, queues, get_features(db_instance))

    assert handled is True
    assert sent_calls == [(thread.sender_number, "Bom dia! Abrimos das 8h as 18h.")]

    async with async_session() as db:
        reloaded_thread = await db.get(ConversationThread, thread.id)
        assert reloaded_thread.ai_paused is False
        assert reloaded_thread.escalated is False
        assert reloaded_thread.queue_status == QueueStatus.NONE


async def test_escalate_for_ai_failure_still_replies_when_no_queue_is_configured(instance, monkeypatch):
    """Defensive edge case: an instance with zero attendance queues (should never happen in
    production - every instance gets a default queue on creation - but the customer-facing
    message is the priority, not the queue invariant)."""
    from app.services.queue import escalate_for_ai_failure

    sent_calls = []

    async def _fake_send(whatsapp_instance_name, number, text):
        sent_calls.append((number, text))

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    thread = await _fresh_thread(instance)
    parsed = ParsedInboundMessage(sender_number=thread.sender_number, text="oi")

    async with async_session() as db:
        db_instance = await db.get(Instance, instance.id)
        db_thread = await db.get(ConversationThread, thread.id)
        await escalate_for_ai_failure(db, db_instance, parsed, db_thread, queues=[])

    assert len(sent_calls) == 1

    async with async_session() as db:
        reloaded_thread = await db.get(ConversationThread, thread.id)
        assert reloaded_thread.ai_paused is True
        assert reloaded_thread.escalated is True
        # No queue was available to route into, so the thread never actually entered QUEUED.
        assert reloaded_thread.queue_status == QueueStatus.NONE


# --- webhooks._maybe_auto_reply: the outer pipeline never raises, even on provider failure ------


async def test_maybe_auto_reply_never_raises_and_still_replies_when_ai_provider_fails(instance, monkeypatch):
    monkeypatch.setattr(OpenAiCompatibleProvider, "reply", _raise_timeout)
    sent_calls = []

    async def _fake_send(whatsapp_instance_name, number, text):
        sent_calls.append((number, text))

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    thread = await _fresh_thread(instance)
    queues = await _queues(instance)
    parsed = ParsedInboundMessage(sender_number=thread.sender_number, text="voces tem entrega?")

    async with async_session() as db:
        db_instance = await db.get(Instance, instance.id)
        db_thread = await db.get(ConversationThread, thread.id)
        # Must not raise - this is exactly what keeps receive_webhook returning 200 to Meta.
        await _maybe_auto_reply(db, db_instance, parsed, db_thread, queues)

    assert len(sent_calls) == 1
    assert "instabilidade tecnica" in sent_calls[0][1]
