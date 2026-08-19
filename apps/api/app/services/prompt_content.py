from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance import Instance
from app.models.prompt_version import PromptVersion


async def get_current_prompt_version(db: AsyncSession, instance: Instance) -> PromptVersion | None:
    if instance.current_prompt_version_id is None:
        return None
    return await db.get(PromptVersion, instance.current_prompt_version_id)


async def get_current_prompt_content(db: AsyncSession, instance: Instance) -> str:
    version = await get_current_prompt_version(db, instance)
    return version.content if version else ""
