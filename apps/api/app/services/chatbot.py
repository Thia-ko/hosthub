"""Deterministic, non-AI reply engine ("chatbot sem IA"): a keyword/numbered-menu tree per
instance, an alternative to the LLM auto-reply for cost-sensitive plans - see
app.services.plans.InstanceFeatures.chatbot_enabled. Tree traversal position is tracked per
conversation on ConversationThread.chatbot_node_id. Wired into the inbound webhook flow by
app.api.v1.routers.webhooks._maybe_auto_reply, which tries this before the AI path."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chatbot_node import ChatbotNode
from app.models.conversation_thread import ConversationThread
from app.utils.json_utils import safe_parse_json_array

# Reserved phrases that always jump back to the root menu, from anywhere in the tree - lets a
# customer escape a sub-menu without a dedicated "back" node on every branch.
RESET_KEYWORDS = ("menu", "voltar", "inicio", "início")


@dataclass
class ChatbotReply:
    text: str
    # Where the thread should be parked after this reply - None means "back at the root, no
    # active sub-menu" (a leaf answer resets here so the next message starts a fresh topic).
    next_node_id: uuid.UUID | None


async def get_root_node(db: AsyncSession, instance_id: uuid.UUID) -> ChatbotNode | None:
    result = await db.execute(
        select(ChatbotNode).where(ChatbotNode.instance_id == instance_id, ChatbotNode.parent_id.is_(None))
    )
    return result.scalar_one_or_none()


async def get_children(db: AsyncSession, node_id: uuid.UUID) -> list[ChatbotNode]:
    result = await db.execute(
        select(ChatbotNode).where(ChatbotNode.parent_id == node_id).order_by(ChatbotNode.order_index)
    )
    return list(result.scalars().all())


def format_menu(children: list[ChatbotNode]) -> str:
    return "\n".join(f"{index}. {child.label}" for index, child in enumerate(children, start=1))


def match_child(text: str, children: list[ChatbotNode]) -> ChatbotNode | None:
    """Matches the customer's message against `children`: first by exact numeric position
    (1-indexed, the way format_menu displays it), then by keyword substring - first match wins."""
    stripped = text.strip()
    if stripped.isdigit():
        index = int(stripped)
        if 1 <= index <= len(children):
            return children[index - 1]
    normalized = text.lower()
    for child in children:
        keywords = safe_parse_json_array(child.keywords)
        if any(keyword.lower() in normalized for keyword in keywords):
            return child
    return None


def is_reset_keyword(text: str) -> bool:
    return text.strip().lower() in RESET_KEYWORDS


async def _root_reply(db: AsyncSession, root: ChatbotNode) -> ChatbotReply:
    children = await get_children(db, root.id)
    text = root.message + (f"\n\n{format_menu(children)}" if children else "")
    return ChatbotReply(text=text, next_node_id=root.id)


async def handle_message(
    db: AsyncSession, instance_id: uuid.UUID, thread: ConversationThread, text: str
) -> ChatbotReply | None:
    """Advances the chatbot tree by one step for an inbound message and returns the reply to
    send, or None if the instance has no root node configured (chatbot inactive - caller should
    fall back to whatever else it does, e.g. the AI path)."""
    root = await get_root_node(db, instance_id)
    if root is None:
        return None

    if is_reset_keyword(text) or thread.chatbot_node_id is None:
        return await _root_reply(db, root)

    current = await db.get(ChatbotNode, thread.chatbot_node_id)
    if current is None or current.instance_id != instance_id:
        # Node was deleted, or the thread predates a tree rebuild - restart clean.
        return await _root_reply(db, root)

    children = await get_children(db, current.id)
    if not children:
        # Defensive: a leaf always resets next_node_id to None on the previous turn, so this
        # shouldn't normally be reachable - but fail back to the root rather than a dead end.
        return await _root_reply(db, root)

    matched = match_child(text, children)
    if matched is None:
        text_out = f"Não entendi. Escolha uma das opções:\n\n{format_menu(children)}"
        return ChatbotReply(text=text_out, next_node_id=current.id)

    grandchildren = await get_children(db, matched.id)
    text_out = matched.message + (f"\n\n{format_menu(grandchildren)}" if grandchildren else "")
    next_node_id = matched.id if grandchildren else None
    return ChatbotReply(text=text_out, next_node_id=next_node_id)
