import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_owned_instance
from app.db.session import get_db
from app.models.attendant_pattern import AttendantPattern
from app.models.extracted_data import ExtractedData
from app.models.faq_item import FaqItem
from app.models.instance import Instance
from app.models.prompt_version import PromptVersion
from app.schemas.analytics import (
    AnalyticsOverviewOut,
    AttendantPatternOut,
    DataReadinessOut,
    ExtractedDataCreateRequest,
    ExtractedDataOut,
    ExtractedDataUpdateRequest,
    FaqCreateRequest,
    FaqItemOut,
    FaqUpdateRequest,
    GeneratedPromptOut,
)
from app.schemas.prompt_version import PromptVersionDetail
from app.services.prompt_generator import generate_prompt_from_data, get_data_readiness
from app.utils.json_utils import safe_parse_json_array

router = APIRouter(prefix="/instances/{instance_id}/analytics", tags=["analytics"])


def _pattern_out(pattern: AttendantPattern) -> AttendantPatternOut:
    return AttendantPatternOut(
        id=pattern.id,
        pattern_type=pattern.pattern_type,
        description=pattern.description,
        examples=safe_parse_json_array(pattern.examples),
        frequency=pattern.frequency,
        created_at=pattern.created_at,
        updated_at=pattern.updated_at,
    )


@router.get("/overview", response_model=AnalyticsOverviewOut)
async def get_overview(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> AnalyticsOverviewOut:
    readiness = await get_data_readiness(db, instance.id)
    pending_id = await db.scalar(
        select(PromptVersion.id)
        .where(PromptVersion.instance_id == instance.id, PromptVersion.is_pending.is_(True))
        .limit(1)
    )
    return AnalyticsOverviewOut(
        analyzed_conversations=readiness["analyzed_conversations"],
        total_faqs=readiness["total_faqs"],
        total_extracted=readiness["total_extracted"],
        total_patterns=readiness["total_patterns"],
        pending_prompt=pending_id is not None,
    )


# ─── FAQs ────────────────────────────────────────────────────────────────────


@router.get("/faqs", response_model=list[FaqItemOut])
async def get_faqs(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[FaqItem]:
    result = await db.execute(
        select(FaqItem).where(FaqItem.instance_id == instance.id).order_by(FaqItem.frequency.desc())
    )
    return list(result.scalars().all())


@router.post("/faqs", response_model=FaqItemOut)
async def create_faq(
    payload: FaqCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> FaqItem:
    faq = FaqItem(
        instance_id=instance.id,
        question=payload.question,
        answer=payload.answer,
        category=payload.category,
        asked_by=payload.asked_by,
    )
    db.add(faq)
    await db.commit()
    await db.refresh(faq)
    return faq


async def _get_faq(db: AsyncSession, instance: Instance, faq_id: uuid.UUID) -> FaqItem:
    result = await db.execute(select(FaqItem).where(FaqItem.id == faq_id, FaqItem.instance_id == instance.id))
    faq = result.scalar_one_or_none()
    if faq is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="FAQ nao encontrada")
    return faq


@router.put("/faqs/{faq_id}", response_model=FaqItemOut)
async def update_faq(
    faq_id: uuid.UUID,
    payload: FaqUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> FaqItem:
    faq = await _get_faq(db, instance, faq_id)
    if payload.question is not None:
        faq.question = payload.question
    if payload.answer is not None:
        faq.answer = payload.answer
    if payload.category is not None:
        faq.category = payload.category
    await db.commit()
    await db.refresh(faq)
    return faq


@router.delete("/faqs/{faq_id}", response_model=dict)
async def delete_faq(
    faq_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    faq = await _get_faq(db, instance, faq_id)
    await db.delete(faq)
    await db.commit()
    return {"deleted": True}


# ─── Patterns ────────────────────────────────────────────────────────────────


@router.get("/patterns", response_model=list[AttendantPatternOut])
async def get_patterns(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[AttendantPatternOut]:
    result = await db.execute(
        select(AttendantPattern)
        .where(AttendantPattern.instance_id == instance.id)
        .order_by(AttendantPattern.frequency.desc())
    )
    return [_pattern_out(pattern) for pattern in result.scalars().all()]


# ─── Extracted data ────────────────────────────────────────────────────────────


@router.get("/extracted-data", response_model=list[ExtractedDataOut])
async def get_extracted_data(
    category: str | None = Query(default=None),
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> list[ExtractedData]:
    query = select(ExtractedData).where(ExtractedData.instance_id == instance.id)
    if category is not None:
        query = query.where(ExtractedData.category == category)
    result = await db.execute(query.order_by(ExtractedData.category, ExtractedData.occurrences.desc()))
    return list(result.scalars().all())


@router.post("/extracted-data", response_model=ExtractedDataOut)
async def create_extracted_data(
    payload: ExtractedDataCreateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> ExtractedData:
    existing_result = await db.execute(
        select(ExtractedData).where(
            ExtractedData.instance_id == instance.id,
            ExtractedData.category == payload.category,
            ExtractedData.key == payload.key,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ja existe um dado com essa categoria/chave")

    item = ExtractedData(
        instance_id=instance.id,
        category=payload.category,
        key=payload.key,
        value=payload.value,
        confidence=1.0,
        source="manual",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def _get_extracted_data(db: AsyncSession, instance: Instance, data_id: uuid.UUID) -> ExtractedData:
    result = await db.execute(
        select(ExtractedData).where(ExtractedData.id == data_id, ExtractedData.instance_id == instance.id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dado nao encontrado")
    return item


@router.put("/extracted-data/{data_id}", response_model=ExtractedDataOut)
async def update_extracted_data(
    data_id: uuid.UUID,
    payload: ExtractedDataUpdateRequest,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> ExtractedData:
    item = await _get_extracted_data(db, instance, data_id)
    item.value = payload.value
    item.confidence = 1.0
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/extracted-data/{data_id}", response_model=dict)
async def delete_extracted_data(
    data_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    item = await _get_extracted_data(db, instance, data_id)
    await db.delete(item)
    await db.commit()
    return {"deleted": True}


# ─── Prompt generation ────────────────────────────────────────────────────────


@router.get("/readiness", response_model=DataReadinessOut)
async def get_readiness(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> DataReadinessOut:
    readiness = await get_data_readiness(db, instance.id)
    return DataReadinessOut(**readiness)


@router.post("/generate-prompt", response_model=GeneratedPromptOut)
async def generate_prompt(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> PromptVersion:
    version = await generate_prompt_from_data(db, instance)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ainda nao ha dados suficientes (nenhuma conversa analisada) para gerar um prompt",
        )
    return version


@router.get("/pending-prompt", response_model=PromptVersionDetail | None)
async def get_pending_prompt(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> PromptVersion | None:
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.instance_id == instance.id, PromptVersion.is_pending.is_(True))
        .order_by(PromptVersion.version_number.desc())
    )
    return result.scalars().first()


@router.post("/pending-prompt/{version_id}/approve", response_model=dict)
async def approve_pending_prompt(
    version_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.id == version_id, PromptVersion.instance_id == instance.id, PromptVersion.is_pending.is_(True)
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt pendente nao encontrado")
    version.is_pending = False
    instance.current_prompt_version_id = version.id
    await db.commit()
    return {"prompt_version_id": str(version.id), "version_number": version.version_number}


@router.post("/pending-prompt/{version_id}/reject", response_model=dict)
async def reject_pending_prompt(
    version_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(PromptVersion).where(
            PromptVersion.id == version_id, PromptVersion.instance_id == instance.id, PromptVersion.is_pending.is_(True)
        )
    )
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt pendente nao encontrado")
    await db.delete(version)
    await db.commit()
    return {"rejected": True}
