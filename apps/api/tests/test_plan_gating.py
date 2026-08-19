"""Integration tests proving each plan-gated router endpoint actually enforces
app.services.plans.get_features against a real STARTER-plan instance (the default plan, which
includes AI but not campaigns/API access) and that ENTERPRISE unlocks them. Hits the real
database (async_session), same convention as test_campaigns.py; router functions are called
directly with explicit keyword arguments (bypasses FastAPI's Depends resolution)."""

import json
import uuid

import httpx
import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1.routers import api_keys as api_keys_router
from app.api.v1.routers import campaigns as campaigns_router
from app.api.v1.routers import outbound_webhooks as outbound_webhooks_router
from app.core.api_key_auth import require_scope
from app.db.session import async_session
from app.models.api_key import ApiKey
from app.models.campaign import Campaign
from app.models.instance import Instance, InstanceStatus, Plan
from app.models.outbound_webhook_subscription import OutboundWebhookSubscription
from app.models.user import User, UserRole
from app.schemas.api_key import ApiKeyCreateRequest
from app.schemas.campaign import CampaignCreateRequest
from app.schemas.outbound_webhook import OutboundWebhookSubscriptionCreateRequest
from app.services.api_keys import PROMPT_READ, generate_api_key
from app.services.outbound_webhooks import MESSAGE_RECEIVED, dispatch_event


@pytest.fixture
async def make_instance():
    """Factory fixture: yields a function creating a real, persisted Instance+owner on a given
    plan. All created instances/owners are torn down together regardless of how many were made."""
    created_ids: list[tuple[uuid.UUID, uuid.UUID]] = []

    async def _make(plan: Plan) -> Instance:
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
                plan=plan,
            )
            db.add(inst)
            await db.commit()
            await db.refresh(inst)
            created_ids.append((inst.id, owner.id))
            return inst

    yield _make

    async with async_session() as db:
        for instance_id, owner_id in created_ids:
            await db.execute(ApiKey.__table__.delete().where(ApiKey.instance_id == instance_id))
            await db.execute(Campaign.__table__.delete().where(Campaign.instance_id == instance_id))
            await db.execute(
                OutboundWebhookSubscription.__table__.delete().where(
                    OutboundWebhookSubscription.instance_id == instance_id
                )
            )
            await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
            await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


# --- campaigns -------------------------------------------------------------------------------


async def test_create_campaign_blocked_on_starter_plan(make_instance):
    instance = await make_instance(Plan.STARTER)
    async with async_session() as db:
        owner = await db.get(User, instance.owner_user_id)
        with pytest.raises(HTTPException) as exc_info:
            await campaigns_router.create_campaign(
                payload=CampaignCreateRequest(name="Promo", message="Ola!"),
                background_tasks=BackgroundTasks(),
                instance=instance,
                user=owner,
                db=db,
            )

    assert exc_info.value.status_code == 403


async def test_create_campaign_allowed_on_pro_plan(make_instance):
    instance = await make_instance(Plan.PRO)
    async with async_session() as db:
        owner = await db.get(User, instance.owner_user_id)
        result = await campaigns_router.create_campaign(
            payload=CampaignCreateRequest(name="Promo", message="Ola!"),
            background_tasks=BackgroundTasks(),
            instance=instance,
            user=owner,
            db=db,
        )

    assert result.name == "Promo"


# --- api_keys ----------------------------------------------------------------------------------


async def test_create_api_key_blocked_on_starter_plan(make_instance):
    instance = await make_instance(Plan.STARTER)
    async with async_session() as db:
        owner = await db.get(User, instance.owner_user_id)
        with pytest.raises(HTTPException) as exc_info:
            await api_keys_router.create_api_key(
                payload=ApiKeyCreateRequest(name="key", scopes=[PROMPT_READ]),
                instance=instance,
                user=owner,
                db=db,
            )

    assert exc_info.value.status_code == 403


async def test_create_api_key_allowed_with_explicit_override_on_starter_plan(make_instance):
    instance = await make_instance(Plan.STARTER)
    async with async_session() as db:
        fresh = await db.get(Instance, instance.id)
        fresh.api_access_enabled_override = True
        await db.commit()

    async with async_session() as db:
        owner = await db.get(User, instance.owner_user_id)
        fresh = await db.get(Instance, instance.id)
        created = await api_keys_router.create_api_key(
            payload=ApiKeyCreateRequest(name="key", scopes=[PROMPT_READ]),
            instance=fresh,
            user=owner,
            db=db,
        )

    assert created.key.startswith("hhk_")


# --- outbound_webhooks ---------------------------------------------------------------------


async def test_create_outbound_webhook_blocked_on_starter_plan(make_instance):
    instance = await make_instance(Plan.STARTER)
    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await outbound_webhooks_router.create_subscription(
                payload=OutboundWebhookSubscriptionCreateRequest(
                    url="https://example.com/hook", events=[MESSAGE_RECEIVED]
                ),
                instance=instance,
                db=db,
            )

    assert exc_info.value.status_code == 403


# --- require_scope (data plane) -------------------------------------------------------------


async def test_require_scope_blocked_on_starter_plan_even_with_a_valid_key(make_instance):
    instance = await make_instance(Plan.STARTER)
    raw_key, prefix, key_hash = generate_api_key()
    async with async_session() as db:
        db.add(
            ApiKey(
                instance_id=instance.id,
                name="key",
                key_prefix=prefix,
                key_hash=key_hash,
                scopes=json.dumps([PROMPT_READ]),
                created_by_user_id=instance.owner_user_id,
            )
        )
        await db.commit()

    dependency = require_scope(PROMPT_READ)
    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(authorization=f"Bearer {raw_key}", db=db)

    assert exc_info.value.status_code == 403


# --- dispatch_event (data plane) -------------------------------------------------------------


async def test_dispatch_event_skips_delivery_on_starter_plan(make_instance, monkeypatch):
    instance = await make_instance(Plan.STARTER)
    async with async_session() as db:
        db.add(
            OutboundWebhookSubscription(
                instance_id=instance.id, url="https://example.com/hook", events=json.dumps([MESSAGE_RECEIVED])
            )
        )
        await db.commit()

    called = False

    async def _fake_post(self, *args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("should not be called on a plan without API access")

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)

    await dispatch_event(instance.id, MESSAGE_RECEIVED, {"sender_number": "5511999999999"})

    assert called is False
