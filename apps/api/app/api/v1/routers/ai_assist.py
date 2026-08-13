import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_owned_instance
from app.db.session import get_db
from app.models.ai_assist_request import AiAssistRequest, AiAssistStatus
from app.models.instance import Instance
from app.models.prompt_version import PromptVersion, PromptVersionSource
from app.models.user import User
from app.schemas.ai_assist import AiAssistSuggestRequest, AiAssistSuggestResponse, AiAssistUsageOut
from app.services.ai_assist_budget import get_daily_limit, get_usage_today, next_reset_at
from app.services.ai_assist_provider import AiAssistProvider, get_ai_assist_provider

router = APIRouter(prefix="/instances/{instance_id}/ai-assist", tags=["ai-assist"])


async def _get_current_prompt_content(db: AsyncSession, instance: Instance) -> str:
    if instance.current_prompt_version_id is None:
        return ""
    version = await db.get(PromptVersion, instance.current_prompt_version_id)
    return version.content if version else ""


async def _get_request(db: AsyncSession, instance: Instance, request_id: uuid.UUID) -> AiAssistRequest:
    result = await db.execute(
        select(AiAssistRequest).where(
            AiAssistRequest.id == request_id, AiAssistRequest.instance_id == instance.id
        )
    )
    ai_request = result.scalar_one_or_none()
    if ai_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sugestao nao encontrada")
    return ai_request


@router.get("/usage", response_model=AiAssistUsageOut)
async def get_usage(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> AiAssistUsageOut:
    used_today = await get_usage_today(db, instance.id)
    return AiAssistUsageOut(used_today=used_today, limit=get_daily_limit(instance), resets_at=next_reset_at())


@router.post("/suggest", response_model=AiAssistSuggestResponse)
async def suggest(
    payload: AiAssistSuggestRequest,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    provider: AiAssistProvider = Depends(get_ai_assist_provider),
) -> AiAssistSuggestResponse:
    used_today = await get_usage_today(db, instance.id)
    limit = get_daily_limit(instance)
    if used_today >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite diario de tokens do assistente de IA atingido",
            headers={"X-Resets-At": next_reset_at().isoformat()},
        )

    if not settings.AI_ASSIST_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Assistente de IA nao configurado: defina AI_ASSIST_API_KEY",
        )

    current_content = await _get_current_prompt_content(db, instance)
    try:
        new_content, prompt_tokens, completion_tokens = await provider.suggest(current_content, payload.instruction)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Nao foi possivel gerar sugestao com o provedor de IA configurado",
        )

    ai_request = AiAssistRequest(
        instance_id=instance.id,
        user_id=user.id,
        instruction=payload.instruction,
        suggested_content=new_content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        status=AiAssistStatus.SUGGESTED,
    )
    db.add(ai_request)
    await db.commit()
    await db.refresh(ai_request)

    return AiAssistSuggestResponse(
        ai_assist_request_id=ai_request.id,
        suggested_content=new_content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )


@router.post("/suggest/{ai_assist_request_id}/apply", response_model=dict)
async def apply_suggestion(
    ai_assist_request_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ai_request = await _get_request(db, instance, ai_assist_request_id)
    if ai_request.status != AiAssistStatus.SUGGESTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sugestao ja foi aplicada ou descartada")

    next_number_result = await db.execute(
        select(func.coalesce(func.max(PromptVersion.version_number), 0)).where(
            PromptVersion.instance_id == instance.id
        )
    )
    next_number = next_number_result.scalar_one() + 1

    version = PromptVersion(
        instance_id=instance.id,
        version_number=next_number,
        content=ai_request.suggested_content or "",
        source=PromptVersionSource.AI_ASSIST,
        change_note=f"Assistente de IA: {ai_request.instruction[:200]}",
        created_by_user_id=user.id,
    )
    db.add(version)
    await db.flush()

    instance.current_prompt_version_id = version.id
    ai_request.status = AiAssistStatus.APPLIED
    ai_request.resulting_prompt_version_id = version.id
    await db.commit()

    return {"prompt_version_id": str(version.id), "version_number": version.version_number}


@router.post("/suggest/{ai_assist_request_id}/discard", response_model=dict)
async def discard_suggestion(
    ai_assist_request_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ai_request = await _get_request(db, instance, ai_assist_request_id)
    if ai_request.status != AiAssistStatus.SUGGESTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sugestao ja foi aplicada ou descartada")
    ai_request.status = AiAssistStatus.DISCARDED
    await db.commit()
    return {"discarded": True}
