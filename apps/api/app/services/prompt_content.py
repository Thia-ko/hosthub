from sqlalchemy.ext.asyncio import AsyncSession

from app.models.instance import Instance
from app.models.prompt_version import PromptVersion


async def get_current_prompt_content(db: AsyncSession, instance: Instance) -> str:
    if instance.current_prompt_version_id is None:
        return ""
    version = await db.get(PromptVersion, instance.current_prompt_version_id)
    return version.content if version else ""
