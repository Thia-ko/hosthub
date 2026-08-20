import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import require_admin
from app.core.rate_limit import rate_limit_demo_ip, rate_limit_public_stats_ip
from app.db.session import get_db
from app.models.demo_lead import DemoLead
from app.schemas.dashboard import PublicPlatformStats
from app.schemas.demo import (
    DemoChatRequest,
    DemoChatResponse,
    DemoLeadContactedUpdate,
    DemoLeadCreate,
    DemoLeadOut,
)
from app.services import demo_sandbox
from app.services.ai_assist_provider import AiAssistProvider, get_ai_assist_provider
from app.services.dashboard_stats import get_resolution_stats

router = APIRouter(prefix="/demo", tags=["demo"])


def _lead_out(lead: DemoLead) -> DemoLeadOut:
    return DemoLeadOut(
        id=lead.id,
        name=lead.name,
        contact=lead.contact,
        business_name=lead.business_name,
        note=lead.note,
        created_at=lead.created_at,
        contacted_at=lead.contacted_at,
    )


@router.post("/chat", response_model=DemoChatResponse, dependencies=[Depends(rate_limit_demo_ip)])
async def demo_chat(
    payload: DemoChatRequest,
    db: AsyncSession = Depends(get_db),
    provider: AiAssistProvider = Depends(get_ai_assist_provider),
) -> DemoChatResponse:
    await demo_sandbox.check_session_budget(db, payload.session_id)
    await demo_sandbox.check_daily_budget(db)

    if not provider.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Demonstracao indisponivel no momento",
        )

    history = [{"role": item.role, "content": item.content} for item in payload.history]
    try:
        reply, prompt_tokens, completion_tokens = await provider.reply(
            demo_sandbox.DEMO_SYSTEM_PROMPT,
            history,
            payload.message,
            max_tokens=settings.DEMO_REPLY_MAX_TOKENS,
        )
    except httpx.HTTPError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Nao foi possivel gerar resposta da demonstracao",
        )

    await demo_sandbox.record_usage(db, payload.session_id, prompt_tokens, completion_tokens)
    remaining = max(
        0,
        demo_sandbox.MAX_MESSAGES_PER_SESSION - await demo_sandbox.session_message_count(db, payload.session_id),
    )
    return DemoChatResponse(reply=reply, messages_remaining=remaining)


@router.post("/leads", response_model=DemoLeadOut, status_code=status.HTTP_201_CREATED)
async def create_demo_lead(payload: DemoLeadCreate, db: AsyncSession = Depends(get_db)) -> DemoLeadOut:
    lead = DemoLead(
        name=payload.name,
        contact=payload.contact,
        business_name=payload.business_name,
        note=payload.note,
    )
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return _lead_out(lead)


@router.get("/leads", response_model=list[DemoLeadOut], dependencies=[Depends(require_admin)])
async def list_demo_leads(db: AsyncSession = Depends(get_db)) -> list[DemoLeadOut]:
    result = await db.execute(select(DemoLead).order_by(DemoLead.created_at.desc()))
    return [_lead_out(lead) for lead in result.scalars().all()]


@router.patch("/leads/{lead_id}", response_model=DemoLeadOut, dependencies=[Depends(require_admin)])
async def update_demo_lead(
    lead_id: uuid.UUID, payload: DemoLeadContactedUpdate, db: AsyncSession = Depends(get_db)
) -> DemoLeadOut:
    lead = await db.get(DemoLead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead nao encontrado")
    lead.contacted_at = datetime.now(timezone.utc) if payload.contacted else None
    await db.commit()
    await db.refresh(lead)
    return _lead_out(lead)


@router.get("/stats", response_model=PublicPlatformStats, dependencies=[Depends(rate_limit_public_stats_ip)])
async def get_public_stats(db: AsyncSession = Depends(get_db)) -> PublicPlatformStats:
    """Platform-wide aggregate (every instance, no per-tenant breakdown) - powers the landing
    page's live ticker. Same query the admin portfolio overview uses
    (dashboard_stats.get_resolution_stats), just public and unscoped."""
    window_days = 7
    stats = await get_resolution_stats(db, days=window_days)
    return PublicPlatformStats(
        ai_resolved_threads=stats.ai_resolved_threads,
        resolution_rate_pct=stats.resolution_rate_pct,
        estimated_hours_saved=stats.estimated_hours_saved,
        window_days=window_days,
    )
