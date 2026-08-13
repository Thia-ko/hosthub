import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_owned_instance
from app.db.session import get_db
from app.models.instance import Instance
from app.models.prompt_version import PromptVersion, PromptVersionSource
from app.models.user import User
from app.schemas.prompt_version import (
    PromptVersionCreateRequest,
    PromptVersionDetail,
    PromptVersionDiffResponse,
    PromptVersionDiffSide,
    PromptVersionSummary,
)

router = APIRouter(prefix="/instances/{instance_id}/prompt-versions", tags=["prompt-versions"])


async def _get_version(db: AsyncSession, instance: Instance, version_id: uuid.UUID) -> PromptVersion:
    result = await db.execute(
        select(PromptVersion).where(PromptVersion.id == version_id, PromptVersion.instance_id == instance.id)
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Versao de prompt nao encontrada")
    return version


@router.get("", response_model=list[PromptVersionSummary])
async def list_prompt_versions(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[PromptVersion]:
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.instance_id == instance.id)
        .order_by(PromptVersion.version_number.desc())
    )
    return list(result.scalars().all())


@router.get("/diff", response_model=PromptVersionDiffResponse)
async def diff_prompt_versions(
    from_: uuid.UUID = Query(..., alias="from"),
    to: uuid.UUID = Query(...),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> PromptVersionDiffResponse:
    from_version = await _get_version(db, instance, from_)
    to_version = await _get_version(db, instance, to)
    return PromptVersionDiffResponse(
        **{
            "from": PromptVersionDiffSide(version_number=from_version.version_number, content=from_version.content),
            "to": PromptVersionDiffSide(version_number=to_version.version_number, content=to_version.content),
        }
    )


@router.get("/{version_id}", response_model=PromptVersionDetail)
async def get_prompt_version(
    version_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> PromptVersion:
    return await _get_version(db, instance, version_id)


@router.post("", response_model=PromptVersionDetail)
async def create_prompt_version(
    payload: PromptVersionCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PromptVersion:
    next_number_result = await db.execute(
        select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
            PromptVersion.instance_id == instance.id
        )
    )
    next_number = next_number_result.scalar_one() + 1

    version = PromptVersion(
        instance_id=instance.id,
        version_number=next_number,
        content=payload.content,
        source=PromptVersionSource.MANUAL,
        change_note=payload.change_note,
        created_by_user_id=user.id,
    )
    db.add(version)
    await db.flush()
    instance.current_prompt_version_id = version.id
    await db.commit()
    await db.refresh(version)
    return version
