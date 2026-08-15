import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_owned_instance
from app.db.session import get_db
from app.models.campaign import Campaign
from app.models.instance import Instance
from app.models.user import User
from app.schemas.campaign import CampaignCreateRequest, CampaignOut
from app.services.campaigns import send_campaign

router = APIRouter(prefix="/instances/{instance_id}/campaigns", tags=["campaigns"])


def _out(campaign: Campaign) -> CampaignOut:
    return CampaignOut(
        id=campaign.id,
        name=campaign.name,
        message=campaign.message,
        status=campaign.status,
        total_recipients=campaign.total_recipients,
        sent_count=campaign.sent_count,
        skipped_count=campaign.skipped_count,
        failed_count=campaign.failed_count,
        created_at=campaign.created_at,
    )


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(
    instance: Instance = Depends(get_owned_instance), db: AsyncSession = Depends(get_db)
) -> list[CampaignOut]:
    result = await db.execute(
        select(Campaign).where(Campaign.instance_id == instance.id).order_by(Campaign.created_at.desc())
    )
    return [_out(campaign) for campaign in result.scalars().all()]


@router.post("", response_model=CampaignOut)
async def create_campaign(
    payload: CampaignCreateRequest,
    background_tasks: BackgroundTasks,
    instance: Instance = Depends(get_owned_instance),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    """Creates the campaign and immediately queues it for sending in the background - see
    app.services.campaigns.send_campaign. Recipients outside the 24h WhatsApp window are
    skipped automatically, never blocked on here."""
    campaign = Campaign(
        instance_id=instance.id, name=payload.name, message=payload.message, created_by_user_id=user.id
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    background_tasks.add_task(send_campaign, campaign.id)
    return _out(campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(
    campaign_id: uuid.UUID,
    instance: Instance = Depends(get_owned_instance),
    db: AsyncSession = Depends(get_db),
) -> CampaignOut:
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.instance_id == instance.id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campanha nao encontrada")
    return _out(campaign)
