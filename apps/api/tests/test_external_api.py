"""Integration tests for the public external API: app.core.api_key_auth.require_scope (the
Bearer-key auth/scope/rate-limit gate) and app.api.v1.routers.external (prompt/data/messages),
plus app.services.prompt_generator.get_collected_data's JSON-safe shape. These hit the real
database (async_session), same convention as test_campaigns.py - the router functions are called
directly with explicit keyword arguments, which bypasses FastAPI's dependency injection (the
`Depends(...)` defaults are never touched since every parameter is supplied explicitly)."""

import json
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.routers import api_keys as api_keys_router
from app.api.v1.routers import external
from app.core import rate_limit
from app.core.api_key_auth import require_scope
from app.db.session import async_session
from app.models.api_key import ApiKey
from app.models.conversation_message import ConversationMessage, MessageOrigin
from app.models.conversation_thread import ConversationThread
from app.models.extracted_data import ExtractedData
from app.models.faq_item import FaqItem
from app.models.instance import Instance, InstanceStatus
from app.models.user import User, UserRole
from app.schemas.api_key import ApiKeyCreateRequest
from app.schemas.external import ExternalSendMessageRequest
from app.services.api_keys import DATA_READ, MESSAGES_WRITE, PROMPT_READ, generate_api_key, hash_api_key
from app.services.prompt_generator import get_collected_data


@pytest.fixture(autouse=True)
def _reset_rate_limit_hits():
    rate_limit._hits.clear()
    yield
    rate_limit._hits.clear()


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
            whatsapp_instance_name="evo-connection",
        )
        db.add(inst)
        await db.commit()
        await db.refresh(inst)
        instance_id = inst.id
        owner_id = owner.id

    yield inst

    async with async_session() as db:
        await db.execute(ApiKey.__table__.delete().where(ApiKey.instance_id == instance_id))
        await db.execute(ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == instance_id))
        await db.execute(ConversationThread.__table__.delete().where(ConversationThread.instance_id == instance_id))
        await db.execute(ExtractedData.__table__.delete().where(ExtractedData.instance_id == instance_id))
        await db.execute(FaqItem.__table__.delete().where(FaqItem.instance_id == instance_id))
        await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
        await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


async def _make_key(instance: Instance, scopes: list[str], *, active: bool = True) -> str:
    raw_key, prefix, key_hash = generate_api_key()
    async with async_session() as db:
        db.add(
            ApiKey(
                instance_id=instance.id,
                name="test key",
                key_prefix=prefix,
                key_hash=key_hash,
                scopes=json.dumps(scopes),
                active=active,
                created_by_user_id=instance.owner_user_id,
            )
        )
        await db.commit()
    return raw_key


# --- require_scope ------------------------------------------------------------------------------


async def test_require_scope_accepts_a_valid_key_with_the_right_scope(instance):
    raw_key = await _make_key(instance, [PROMPT_READ])
    dependency = require_scope(PROMPT_READ)

    async with async_session() as db:
        resolved = await dependency(authorization=f"Bearer {raw_key}", db=db)

    assert resolved.id == instance.id


async def test_require_scope_rejects_missing_authorization_header(instance):
    dependency = require_scope(PROMPT_READ)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(authorization=None, db=db)

    assert exc_info.value.status_code == 401


async def test_require_scope_rejects_unknown_key(instance):
    dependency = require_scope(PROMPT_READ)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(authorization="Bearer hhk_does-not-exist", db=db)

    assert exc_info.value.status_code == 401


async def test_require_scope_rejects_revoked_key(instance):
    raw_key = await _make_key(instance, [PROMPT_READ], active=False)
    dependency = require_scope(PROMPT_READ)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(authorization=f"Bearer {raw_key}", db=db)

    assert exc_info.value.status_code == 401


async def test_require_scope_rejects_a_key_without_the_needed_scope(instance):
    raw_key = await _make_key(instance, [DATA_READ])
    dependency = require_scope(PROMPT_READ)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(authorization=f"Bearer {raw_key}", db=db)

    assert exc_info.value.status_code == 403


async def test_require_scope_updates_last_used_at(instance):
    raw_key = await _make_key(instance, [PROMPT_READ])
    dependency = require_scope(PROMPT_READ)

    async with async_session() as db:
        await dependency(authorization=f"Bearer {raw_key}", db=db)

    async with async_session() as db:
        result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key)))
        key = result.scalar_one()
        assert key.last_used_at is not None


async def test_require_scope_rate_limits_per_key(instance, monkeypatch):
    raw_key = await _make_key(instance, [PROMPT_READ])
    dependency = require_scope(PROMPT_READ)
    monkeypatch.setattr(rate_limit, "_MAX_REQUESTS_PER_WINDOW", 2)

    async with async_session() as db:
        await dependency(authorization=f"Bearer {raw_key}", db=db)
    async with async_session() as db:
        await dependency(authorization=f"Bearer {raw_key}", db=db)

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await dependency(authorization=f"Bearer {raw_key}", db=db)

    assert exc_info.value.status_code == 429


# --- external.send_message ------------------------------------------------------------------


async def test_send_message_delivers_and_logs_with_api_origin_and_pauses_ai(instance, monkeypatch):
    sent_calls = []

    async def _fake_send(whatsapp_instance_name, number, text):
        sent_calls.append((whatsapp_instance_name, number, text))

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    async with async_session() as db:
        result = await external.send_message(
            payload=ExternalSendMessageRequest(to="5511999999999", text="Ola via API"),
            instance=instance,
            db=db,
        )

    assert sent_calls == [("evo-connection", "5511999999999", "Ola via API")]
    assert result.text == "Ola via API"

    async with async_session() as db:
        message = await db.get(ConversationMessage, result.id)
        assert message.origin == MessageOrigin.API

        thread_result = await db.execute(
            select(ConversationThread).where(
                ConversationThread.instance_id == instance.id, ConversationThread.sender_number == "5511999999999"
            )
        )
        thread = thread_result.scalar_one()
        assert thread.ai_paused is True


# --- prompt_generator.get_collected_data ------------------------------------------------------


async def test_get_collected_data_returns_json_safe_shape(instance):
    async with async_session() as db:
        db.add(
            ExtractedData(instance_id=instance.id, category="business_info", key="nome", value="Padaria do Ze")
        )
        db.add(FaqItem(instance_id=instance.id, question="Voces entregam?", answer="Sim, gratis acima de R$50"))
        await db.commit()

    async with async_session() as db:
        data = await get_collected_data(db, instance.id)

    assert data["business_info"] == [{"key": "nome", "value": "Padaria do Ze"}]
    assert data["products_services"] == []
    assert data["policies"] == []
    assert data["faqs"] == [{"question": "Voces entregam?", "answer": "Sim, gratis acima de R$50"}]


# --- api_keys router (create/list/revoke round trip) -------------------------------------------


async def test_create_api_key_returns_the_raw_key_once_and_persists_only_the_hash(instance):
    async with async_session() as db:
        user = await db.get(User, instance.owner_user_id)
        created = await api_keys_router.create_api_key(
            payload=ApiKeyCreateRequest(name="n8n producao", scopes=[PROMPT_READ, MESSAGES_WRITE]),
            instance=instance,
            user=user,
            db=db,
        )

    assert created.key.startswith("hhk_")
    assert created.scopes == [PROMPT_READ, MESSAGES_WRITE]

    async with async_session() as db:
        result = await db.execute(select(ApiKey).where(ApiKey.id == created.id))
        key = result.scalar_one()
        assert key.key_hash == hash_api_key(created.key)


async def test_revoke_api_key_deactivates_it(instance):
    raw_key = await _make_key(instance, [PROMPT_READ])
    async with async_session() as db:
        result = await db.execute(select(ApiKey).where(ApiKey.key_hash == hash_api_key(raw_key)))
        key = result.scalar_one()
        key_id = key.id

    async with async_session() as db:
        response = await api_keys_router.revoke_api_key(key_id=key_id, instance=instance, db=db)

    assert response == {"revoked": True}

    async with async_session() as db:
        result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
        key = result.scalar_one()
        assert key.active is False
        assert key.revoked_at is not None
