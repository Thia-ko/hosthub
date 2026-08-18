import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.instance import Instance
from app.models.instance_knowledge_file import InstanceKnowledgeFile
from app.schemas.knowledge_files import KnowledgeFileOut, KnowledgeFileUpdateRequest
from app.services.ai_assist_provider import AiAssistProvider, get_ai_assist_provider
from app.services.knowledge_files import save_knowledge_file

router = APIRouter(prefix="/instances/{instance_id}/knowledge-files", tags=["knowledge-files"])


@router.get("", response_model=list[KnowledgeFileOut])
async def list_knowledge_files(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[InstanceKnowledgeFile]:
    result = await db.execute(
        select(InstanceKnowledgeFile)
        .where(InstanceKnowledgeFile.instance_id == instance.id)
        .order_by(InstanceKnowledgeFile.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=KnowledgeFileOut)
async def upload_knowledge_file(
    upload: UploadFile = File(...),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
    provider: AiAssistProvider = Depends(get_ai_assist_provider),
) -> InstanceKnowledgeFile:
    try:
        return await save_knowledge_file(db, instance.id, upload, provider)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


async def _get_knowledge_file(db: AsyncSession, instance: Instance, file_id: uuid.UUID) -> InstanceKnowledgeFile:
    result = await db.execute(
        select(InstanceKnowledgeFile).where(
            InstanceKnowledgeFile.id == file_id, InstanceKnowledgeFile.instance_id == instance.id
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo nao encontrado")
    return item


@router.patch("/{file_id}", response_model=KnowledgeFileOut)
async def update_knowledge_file(
    file_id: uuid.UUID,
    payload: KnowledgeFileUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> InstanceKnowledgeFile:
    item = await _get_knowledge_file(db, instance, file_id)
    if payload.usage_mode is not None:
        item.usage_mode = payload.usage_mode
    if payload.include_next is not None:
        item.include_next = payload.include_next
    if payload.content_text is not None:
        item.content_text = payload.content_text
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{file_id}", response_model=dict)
async def delete_knowledge_file(
    file_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await _get_knowledge_file(db, instance, file_id)
    Path(item.storage_path).unlink(missing_ok=True)
    await db.delete(item)
    await db.commit()
    return {"deleted": True}


@router.get("/{file_id}/content")
async def get_knowledge_file_content(
    file_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    item = await _get_knowledge_file(db, instance, file_id)
    return FileResponse(item.storage_path, media_type=item.content_type, filename=item.filename)
