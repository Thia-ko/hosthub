import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_admin, require_cf_access_header
from app.db.session import get_db
from app.models.prompt_template import PromptTemplate
from app.models.user import User
from app.schemas.prompt_template import (
    PromptTemplateCreateRequest,
    PromptTemplateOut,
    PromptTemplateUpdateRequest,
)

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


async def _get_template(db: AsyncSession, template_id: uuid.UUID) -> PromptTemplate:
    template = await db.get(PromptTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template nao encontrado")
    return template


@router.get("", response_model=list[PromptTemplateOut])
async def list_templates(
    _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[PromptTemplate]:
    result = await db.execute(select(PromptTemplate).order_by(PromptTemplate.niche, PromptTemplate.title))
    return list(result.scalars().all())


@router.post("", response_model=PromptTemplateOut, dependencies=[Depends(require_cf_access_header)])
async def create_template(
    payload: PromptTemplateCreateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PromptTemplate:
    template = PromptTemplate(created_by_admin_id=admin.id, **payload.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.patch("/{template_id}", response_model=PromptTemplateOut, dependencies=[Depends(require_cf_access_header)])
async def update_template(
    template_id: uuid.UUID,
    payload: PromptTemplateUpdateRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PromptTemplate:
    template = await _get_template(db, template_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/{template_id}", dependencies=[Depends(require_cf_access_header)])
async def delete_template(
    template_id: uuid.UUID,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    template = await _get_template(db, template_id)
    await db.delete(template)
    await db.commit()
    return {"deleted": True}
