"""Integration tests for the chatbot tree: app.services.chatbot.handle_message traversal,
app.api.v1.routers.chatbot_nodes CRUD (including the plan gate and the single-root constraint),
and the end-to-end wiring in app.api.v1.routers.webhooks._maybe_auto_reply. Hits the real
database (async_session), same convention as test_campaigns.py / test_plan_gating.py."""

import json
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.routers import chatbot_nodes as chatbot_nodes_router
from app.api.v1.routers.webhooks import _maybe_auto_reply
from app.db.session import async_session
from app.models.chatbot_node import ChatbotNode
from app.models.conversation_message import ConversationMessage, MessageOrigin
from app.models.conversation_thread import ConversationThread
from app.models.instance import Instance, InstanceStatus, Plan
from app.models.user import User, UserRole
from app.schemas.chatbot_node import ChatbotNodeCreateRequest
from app.services.chatbot import handle_message
from app.services.conversation_threads import get_or_create_thread
from app.services.whatsapp_channel import ParsedInboundMessage


@pytest.fixture
async def instance():
    """A real, persisted, chatbot-enabled Instance (STARTER plan + explicit override, since no
    named plan bundles chatbot_enabled by default - see app.services.plans.PLAN_DEFAULTS)."""
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
            chatbot_enabled_override=True,
        )
        db.add(inst)
        await db.commit()
        await db.refresh(inst)
        instance_id = inst.id
        owner_id = owner.id

    yield inst

    async with async_session() as db:
        await db.execute(ConversationMessage.__table__.delete().where(ConversationMessage.instance_id == instance_id))
        await db.execute(ConversationThread.__table__.delete().where(ConversationThread.instance_id == instance_id))
        await db.execute(ChatbotNode.__table__.delete().where(ChatbotNode.instance_id == instance_id))
        await db.execute(Instance.__table__.delete().where(Instance.id == instance_id))
        await db.execute(User.__table__.delete().where(User.id == owner_id))
        await db.commit()


async def _make_node(instance: Instance, *, parent_id=None, label: str, keywords=None, message: str) -> ChatbotNode:
    async with async_session() as db:
        node = ChatbotNode(
            instance_id=instance.id,
            parent_id=parent_id,
            label=label,
            keywords=json.dumps(keywords or []),
            message=message,
        )
        db.add(node)
        await db.commit()
        await db.refresh(node)
        return node


async def _build_tree(instance: Instance) -> dict[str, ChatbotNode]:
    """root -> {Vendas (leaf), Suporte -> {Horario (leaf)}}."""
    root = await _make_node(instance, label="Menu principal", message="Ola! Como posso ajudar?")
    vendas = await _make_node(
        instance, parent_id=root.id, label="Vendas", keywords=["vendas", "comprar"],
        message="Fale com vendas: (11) 1234-5678",
    )
    suporte = await _make_node(
        instance, parent_id=root.id, label="Suporte", keywords=["suporte"], message="Escolha uma opcao:"
    )
    horario = await _make_node(
        instance, parent_id=suporte.id, label="Horario", keywords=["horario"],
        message="Funcionamos de seg a sex, 9h-18h.",
    )
    return {"root": root, "vendas": vendas, "suporte": suporte, "horario": horario}


async def _fresh_thread(instance: Instance) -> ConversationThread:
    async with async_session() as db:
        thread = await get_or_create_thread(db, instance.id, "5511999999999")
        await db.commit()
        await db.refresh(thread)
        return thread


# --- handle_message: traversal -----------------------------------------------------------------


async def test_first_message_returns_root_greeting_and_menu(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "oi")

    assert reply is not None
    assert reply.text == "Ola! Como posso ajudar?\n\n1. Vendas\n2. Suporte"
    assert reply.next_node_id == nodes["root"].id


async def test_no_root_configured_returns_none(instance):
    thread = await _fresh_thread(instance)

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "oi")

    assert reply is None


async def test_selecting_a_leaf_by_number_resets_position_to_none(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)
    thread.chatbot_node_id = nodes["root"].id

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "1")

    assert reply.text == "Fale com vendas: (11) 1234-5678"
    assert reply.next_node_id is None


async def test_selecting_a_submenu_by_keyword_advances_and_shows_its_children(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)
    thread.chatbot_node_id = nodes["root"].id

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "quero falar com o suporte")

    assert reply.text == "Escolha uma opcao:\n\n1. Horario"
    assert reply.next_node_id == nodes["suporte"].id


async def test_unmatched_message_repeats_the_current_menu_without_moving(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)
    thread.chatbot_node_id = nodes["root"].id

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "blablabla")

    assert reply.text == "Não entendi. Escolha uma das opções:\n\n1. Vendas\n2. Suporte"
    assert reply.next_node_id == nodes["root"].id


async def test_reset_keyword_returns_to_root_from_anywhere(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)
    thread.chatbot_node_id = nodes["suporte"].id

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "menu")

    assert reply.next_node_id == nodes["root"].id
    assert "Ola! Como posso ajudar?" in reply.text


async def test_deleted_current_node_falls_back_to_root(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)
    thread.chatbot_node_id = uuid.uuid4()  # not a real node (simulates a stale/deleted position)

    async with async_session() as db:
        reply = await handle_message(db, instance.id, thread, "oi")

    assert reply.next_node_id == nodes["root"].id


# --- chatbot_nodes router: CRUD + gating ------------------------------------------------------


async def test_create_root_node_blocked_without_chatbot_enabled(instance):
    async with async_session() as db:
        fresh = await db.get(Instance, instance.id)
        fresh.chatbot_enabled_override = None  # inherit STARTER's default (chatbot off)
        await db.commit()

    async with async_session() as db:
        fresh = await db.get(Instance, instance.id)
        with pytest.raises(HTTPException) as exc_info:
            await chatbot_nodes_router.create_chatbot_node(
                payload=ChatbotNodeCreateRequest(label="Menu principal", message="Ola!"),
                instance=fresh,
                db=db,
            )

    assert exc_info.value.status_code == 403


async def test_create_second_root_node_is_rejected(instance):
    await _make_node(instance, label="Menu principal", message="Ola!")

    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await chatbot_nodes_router.create_chatbot_node(
                payload=ChatbotNodeCreateRequest(label="Outro menu", message="Oi de novo"),
                instance=instance,
                db=db,
            )

    assert exc_info.value.status_code == 409


async def test_create_child_node_under_a_real_parent(instance):
    root = await _make_node(instance, label="Menu principal", message="Ola!")

    async with async_session() as db:
        created = await chatbot_nodes_router.create_chatbot_node(
            payload=ChatbotNodeCreateRequest(parent_id=root.id, label="Vendas", keywords=["vendas"], message="Oi vendas"),
            instance=instance,
            db=db,
        )

    assert created.parent_id == root.id
    assert created.keywords == ["vendas"]


async def test_create_child_node_with_unknown_parent_is_rejected(instance):
    async with async_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            await chatbot_nodes_router.create_chatbot_node(
                payload=ChatbotNodeCreateRequest(parent_id=uuid.uuid4(), label="X", message="Y"),
                instance=instance,
                db=db,
            )

    assert exc_info.value.status_code == 404


async def test_delete_node_cascades_to_children_and_resets_parked_threads(instance):
    nodes = await _build_tree(instance)
    thread = await _fresh_thread(instance)
    async with async_session() as db:
        fresh_thread = await db.get(ConversationThread, thread.id)
        fresh_thread.chatbot_node_id = nodes["horario"].id
        await db.commit()

    async with async_session() as db:
        response = await chatbot_nodes_router.delete_chatbot_node(
            node_id=nodes["suporte"].id, instance=instance, db=db
        )

    assert response == {"deleted": True}

    async with async_session() as db:
        assert await db.get(ChatbotNode, nodes["suporte"].id) is None
        assert await db.get(ChatbotNode, nodes["horario"].id) is None  # cascaded
        assert await db.get(ChatbotNode, nodes["vendas"].id) is not None  # untouched sibling

        reloaded_thread = await db.get(ConversationThread, thread.id)
        assert reloaded_thread.chatbot_node_id is None  # ON DELETE SET NULL


# --- webhooks._maybe_auto_reply: end-to-end wiring ---------------------------------------------


async def test_maybe_auto_reply_sends_chatbot_greeting_on_first_contact(instance, monkeypatch):
    await _build_tree(instance)
    thread = await _fresh_thread(instance)

    sent_calls = []

    async def _fake_send(whatsapp_instance_name, number, text):
        sent_calls.append((number, text))

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    parsed = ParsedInboundMessage(sender_number="5511999999999", text="oi")

    async with async_session() as db:
        db_instance = await db.get(Instance, instance.id)
        db_thread = await db.get(ConversationThread, thread.id)
        await _maybe_auto_reply(db, db_instance, parsed, db_thread)

    assert len(sent_calls) == 1
    assert sent_calls[0][0] == "5511999999999"
    assert "Ola! Como posso ajudar?" in sent_calls[0][1]

    async with async_session() as db:
        reloaded_thread = await db.get(ConversationThread, thread.id)
        assert reloaded_thread.chatbot_node_id is not None

        result = await db.execute(
            select(ConversationMessage).where(ConversationMessage.instance_id == instance.id)
        )
        messages = result.scalars().all()
        assert any(m.origin == MessageOrigin.CHATBOT for m in messages)


async def test_maybe_auto_reply_skips_chatbot_when_feature_disabled(instance, monkeypatch):
    await _build_tree(instance)
    async with async_session() as db:
        fresh = await db.get(Instance, instance.id)
        fresh.chatbot_enabled_override = False
        await db.commit()

    thread = await _fresh_thread(instance)
    sent_calls = []

    async def _fake_send(*args, **kwargs):
        sent_calls.append(args)

    monkeypatch.setattr("app.services.whatsapp_channel.send_text_message", _fake_send)

    parsed = ParsedInboundMessage(sender_number="5511999999999", text="oi")

    async with async_session() as db:
        db_instance = await db.get(Instance, instance.id)
        db_thread = await db.get(ConversationThread, thread.id)
        await _maybe_auto_reply(db, db_instance, parsed, db_thread)

    # No AI provider is configured in this test environment either, so nothing should be sent
    # at all - the important assertion is that the chatbot path specifically was not taken.
    assert sent_calls == []
    async with async_session() as db:
        reloaded_thread = await db.get(ConversationThread, thread.id)
        assert reloaded_thread.chatbot_node_id is None
