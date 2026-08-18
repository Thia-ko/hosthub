import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import async_session
from app.models.campaign import Campaign, CampaignStatus
from app.models.campaign_recipient import CampaignRecipient, CampaignRecipientStatus
from app.models.conversation_message import ConversationMessage, MessageDirection, MessageKind, MessageOrigin
from app.models.instance import Instance, InstanceStatus
from app.services.conversation_threads import get_or_create_thread
from app.services.whatsapp_channel import WhatsAppChannelError, send_reply

logger = logging.getLogger(__name__)

# WhatsApp/Meta requires a pre-approved message template to contact a customer outside this
# window since their last inbound message; HostHub has no template management, so campaigns
# restrict themselves to customers still inside it rather than risk the number getting
# flagged/blocked for out-of-window free-form sends.
WINDOW = timedelta(hours=24)

# Small pacing delay between sends - gentler on the provider than firing everything at once.
SEND_DELAY_SECONDS = 0.5


async def send_campaign(campaign_id: uuid.UUID) -> None:
    """Background entrypoint (queued via BackgroundTasks right after the campaign is created):
    sends `campaign.message` to every distinct customer who has ever messaged the instance,
    skipping anyone outside the 24h window. Never raises - per-recipient failures are recorded
    on that recipient only, see `_process_recipient`."""
    async with async_session() as db:
        campaign = await db.get(Campaign, campaign_id)
        if campaign is None:
            return
        instance = await db.get(Instance, campaign.instance_id)
        if instance is None or instance.status != InstanceStatus.ACTIVE:
            campaign.status = CampaignStatus.FAILED
            await db.commit()
            return
        instance_id = instance.id
        sender_numbers = list(
            await db.scalars(
                select(ConversationMessage.sender_number)
                .where(ConversationMessage.instance_id == instance_id)
                .distinct()
            )
        )
        campaign.total_recipients = len(sender_numbers)
        await db.commit()

    cutoff = datetime.now(timezone.utc) - WINDOW
    for sender_number in sender_numbers:
        try:
            await _process_recipient(campaign_id, instance_id, sender_number, cutoff)
        except Exception:  # noqa: BLE001 - one bad recipient must never abort the whole campaign
            logger.exception("Campaign %s: unexpected error processing %s", campaign_id, sender_number)
        await asyncio.sleep(SEND_DELAY_SECONDS)

    async with async_session() as db:
        campaign = await db.get(Campaign, campaign_id)
        if campaign is not None:
            campaign.status = CampaignStatus.COMPLETED
            await db.commit()


async def _process_recipient(
    campaign_id: uuid.UUID, instance_id: uuid.UUID, sender_number: str, cutoff: datetime
) -> None:
    async with async_session() as db:
        instance = await db.get(Instance, instance_id)
        campaign = await db.get(Campaign, campaign_id)
        if instance is None or campaign is None:
            return

        latest_inbound = await db.scalar(
            select(ConversationMessage)
            .where(
                ConversationMessage.instance_id == instance_id,
                ConversationMessage.sender_number == sender_number,
                ConversationMessage.direction == MessageDirection.INBOUND,
            )
            .order_by(ConversationMessage.created_at.desc())
            .limit(1)
        )

        if latest_inbound is None or latest_inbound.created_at < cutoff:
            db.add(
                CampaignRecipient(
                    campaign_id=campaign_id, sender_number=sender_number, status=CampaignRecipientStatus.SKIPPED_WINDOW
                )
            )
            campaign.skipped_count += 1
            await db.commit()
            return

        thread = await get_or_create_thread(db, instance_id, sender_number)
        try:
            await send_reply(instance, sender_number, campaign.message, thread.last_whatsbotmais_token)
        except WhatsAppChannelError:
            logger.exception("Campaign %s: failed to send to %s", campaign_id, sender_number)
            db.add(
                CampaignRecipient(
                    campaign_id=campaign_id, sender_number=sender_number, status=CampaignRecipientStatus.FAILED
                )
            )
            campaign.failed_count += 1
            await db.commit()
            return

        db.add(
            ConversationMessage(
                instance_id=instance_id,
                sender_number=sender_number,
                direction=MessageDirection.OUTBOUND,
                kind=MessageKind.TEXT,
                text=campaign.message,
                origin=MessageOrigin.SYSTEM,
            )
        )
        db.add(
            CampaignRecipient(campaign_id=campaign_id, sender_number=sender_number, status=CampaignRecipientStatus.SENT)
        )
        campaign.sent_count += 1
        await db.commit()
