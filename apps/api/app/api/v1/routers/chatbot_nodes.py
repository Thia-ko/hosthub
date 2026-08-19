import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.chatbot_node import ChatbotNode
from app.models.instance import Instance
from app.schemas.chatbot_node import ChatbotNodeCreateRequest, ChatbotNodeOut, ChatbotNodeUpdateRequest
from app.services.plans import get_features
from app.utils.json_utils import safe_parse_json_array

router = APIRouter(prefix="/instances/{instance_id}/chatbot-nodes", tags=["chatbot-nodes"])


def _out(node: ChatbotNode) -> ChatbotNodeOut:
    return ChatbotNodeOut(
        id=node.id,
        parent_id=node.parent_id,
        label=node.label,
        keywords=safe_parse_json_array(node.keywords),
        message=node.message,
        order_index=node.order_index,
        created_at=node.created_at,
    )


@router.get("", response_model=list[ChatbotNodeOut])
async def list_chatbot_nodes(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[ChatbotNodeOut]:
    result = await db.execute(
        select(ChatbotNode).where(ChatbotNode.instance_id == instance.id).order_by(ChatbotNode.order_index)
    )
    return [_out(node) for node in result.scalars().all()]


@router.post("", response_model=ChatbotNodeOut)
async def create_chatbot_node(
    payload: ChatbotNodeCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> ChatbotNodeOut:
    if not get_features(instance).chatbot_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="O plano desta instancia nao inclui o chatbot"
        )

    if payload.parent_id is None:
        existing_root = await db.execute(
            select(ChatbotNode).where(ChatbotNode.instance_id == instance.id, ChatbotNode.parent_id.is_(None))
        )
        if existing_root.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Esta instancia ja tem um menu principal"
            )
    else:
        parent = await db.get(ChatbotNode, payload.parent_id)
        if parent is None or parent.instance_id != instance.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pai nao encontrado")

    node = ChatbotNode(
        instance_id=instance.id,
        parent_id=payload.parent_id,
        label=payload.label,
        keywords=json.dumps(payload.keywords),
        message=payload.message,
        order_index=payload.order_index,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _out(node)


async def _get_node(db: AsyncSession, instance: Instance, node_id: uuid.UUID) -> ChatbotNode:
    result = await db.execute(
        select(ChatbotNode).where(ChatbotNode.id == node_id, ChatbotNode.instance_id == instance.id)
    )
    node = result.scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No nao encontrado")
    return node


@router.put("/{node_id}", response_model=ChatbotNodeOut)
async def update_chatbot_node(
    node_id: uuid.UUID,
    payload: ChatbotNodeUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> ChatbotNodeOut:
    node = await _get_node(db, instance, node_id)
    if payload.label is not None:
        node.label = payload.label
    if payload.keywords is not None:
        node.keywords = json.dumps(payload.keywords)
    if payload.message is not None:
        node.message = payload.message
    if payload.order_index is not None:
        node.order_index = payload.order_index
    await db.commit()
    await db.refresh(node)
    return _out(node)


@router.delete("/{node_id}", response_model=dict)
async def delete_chatbot_node(
    node_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deleting cascades to the whole subtree (ChatbotNode.parent_id ON DELETE CASCADE) and
    resets any customer parked inside it back to the root (ConversationThread.chatbot_node_id
    ON DELETE SET NULL) - both enforced at the DB level, not here."""
    node = await _get_node(db, instance, node_id)
    await db.delete(node)
    await db.commit()
    return {"deleted": True}
