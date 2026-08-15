import asyncio
import logging

from sqlalchemy import select

from app.db.session import async_session
from app.models.instance import Instance
from app.services.csat import maybe_request_feedback
from app.services.prompt_generator import maybe_auto_generate_prompt

logger = logging.getLogger(__name__)

# How often to run every periodic check below. Coarse relative to the shortest interval option
# ("1d" for auto-gen, 4h inactivity for CSAT) - no need for finer granularity, and it keeps the
# idle cost of the loop negligible.
CHECK_INTERVAL_SECONDS = 30 * 60


async def run_background_scheduler() -> None:
    """Background loop started from the app lifespan, running two independent periodic checks:

    1. Prompt auto-generation for instances configured with a time-based interval
       (`Instance.auto_gen_interval` != "off"). Conversation-count-threshold instances (the
       default) don't need this - they're already checked inline whenever a webhook message
       lands, see `app.services.conversation_analyzer.maybe_trigger_analysis`. Without this
       loop, an interval-configured instance with no new incoming messages would never
       auto-generate, because `maybe_auto_generate_prompt` was only ever reachable from that
       same message-driven path.
    2. CSAT: sends the satisfaction question to threads that have gone quiet after our last
       reply (`app.services.csat.maybe_request_feedback`) - also has no other trigger, since
       it fires on the customer's *silence*, not on a new message.
    """
    while True:
        try:
            await _check_all_instances()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Auto-generation scheduler tick failed")
        try:
            await maybe_request_feedback()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("CSAT scheduler tick failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def _check_all_instances() -> None:
    async with async_session() as db:
        result = await db.scalars(
            select(Instance.id).where(
                Instance.auto_generate_prompt.is_(True),
                Instance.auto_gen_interval != "off",
            )
        )
        instance_ids = list(result)

    for instance_id in instance_ids:
        async with async_session() as db:
            instance = await db.get(Instance, instance_id)
            if instance is None:
                continue
            try:
                await maybe_auto_generate_prompt(db, instance)
            except Exception:
                logger.exception("Scheduled auto-generation failed for instance %s", instance_id)
