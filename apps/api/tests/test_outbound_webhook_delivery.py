"""Integration tests for outbound webhook delivery signing (app.services.outbound_webhooks.
dispatch_event) and secret rotation (app.api.v1.routers.outbound_webhooks.regenerate_secret).
Hits the real database (async_session), same convention as test_campaigns.py; the one outbound
HTTP call (httpx.AsyncClient.post) is monkeypatched so no real network call happens."""

import json
import uuid

import httpx
import pytest

from app.api.v1.routers import outbound_webhooks as outbound_webhooks_router
from app.db.session import async_session
from app.models.instance import Instance, InstanceStatus
from app.models.outbound_webhook_subscription import OutboundWebhookSubscription
from app.models.user import User, UserRole
from app.services.outbound_webhooks import (
    MESSAGE_RECEIVED,
    SIGNATURE_HEADER,
    THREAD_ESCALATED,
    dispatch_event,
    sign_payload,
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
        instance_id = inst.id
        owner_id = owner.id

    yield inst

    async with async_session() as db:
        await db.execute(
            OutboundWebhookSubscription.__table__.delete().where(
                OutboundWebhookSubscription.instance_id == instance_id
            )
        )
        await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
        await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


async def _make_subscription(instance: Instance, url: str = "https://example.com/hook") -> OutboundWebhookSubscription:
    async with async_session() as db:
        sub = OutboundWebhookSubscription(
            instance_id=instance.id, url=url, events=json.dumps([MESSAGE_RECEIVED])
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub


async def test_dispatch_event_signs_the_exact_bytes_it_sends(instance, monkeypatch):
    sub = await _make_subscription(instance)
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    async def _fake_post(self, url, content=None, headers=None, **kwargs):
        captured["url"] = url
        captured["content"] = content
        captured["headers"] = headers
        return _FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

    await dispatch_event(instance.id, MESSAGE_RECEIVED, {"sender_number": "5511999999999"})

    assert captured["url"] == sub.url
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["headers"][SIGNATURE_HEADER] == sign_payload(sub.secret, captured["content"])

    body = json.loads(captured["content"])
    assert body["event"] == MESSAGE_RECEIVED
    assert body["instance_id"] == str(instance.id)
    assert body["sender_number"] == "5511999999999"


async def test_dispatch_event_signature_differs_after_secret_rotation(instance, monkeypatch):
    sub = await _make_subscription(instance)
    old_secret = sub.secret
    captured = {}

    class _FakeResponse:
        def raise_for_status(self):
            pass

    async def _fake_post(self, url, content=None, headers=None, **kwargs):
        captured["content"] = content
        captured["headers"] = headers
        return _FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

    async with async_session() as db:
        rotated = await outbound_webhooks_router.regenerate_secret(sub_id=sub.id, instance=instance, db=db)

    assert rotated.secret != old_secret

    await dispatch_event(instance.id, MESSAGE_RECEIVED, {"sender_number": "5511999999999"})

    assert captured["headers"][SIGNATURE_HEADER] == sign_payload(rotated.secret, captured["content"])
    assert captured["headers"][SIGNATURE_HEADER] != sign_payload(old_secret, captured["content"])


async def test_dispatch_event_skips_subscriptions_not_listening_to_the_event(instance, monkeypatch):
    await _make_subscription(instance)  # subscribed only to MESSAGE_RECEIVED
    called = False

    async def _fake_post(self, *args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should not be called for an unsubscribed event")

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

    await dispatch_event(instance.id, THREAD_ESCALATED, {"sender_number": "5511999999999"})

    assert called is False
