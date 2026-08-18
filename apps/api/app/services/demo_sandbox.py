from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.demo_chat_log import DemoChatLog

MAX_MESSAGES_PER_SESSION = 6

DEMO_SYSTEM_PROMPT = (
    "Voce e o atendente de WhatsApp da 'Barbearia Vintage', uma barbearia ficticia usada para "
    "demonstrar a plataforma Hosthub. Dados do negocio (use apenas estes, nao invente outros): "
    "horario de segunda a sabado das 9h as 19h; servicos - corte R$45, barba R$35, combo corte+barba "
    "R$70; endereco Rua das Palmeiras, 120, Centro; agendamento so por esse WhatsApp, sem app. "
    "Responda em portugues, tom simpatico e objetivo, no maximo 3 frases. Deixe claro quando "
    "perguntado que esta e uma demonstracao com dados ficticios."
)


def _today_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def session_message_count(db: AsyncSession, session_id: str) -> int:
    result = await db.execute(
        select(func.count()).select_from(DemoChatLog).where(DemoChatLog.session_id == session_id)
    )
    return result.scalar_one()


async def check_session_budget(db: AsyncSession, session_id: str) -> None:
    count = await session_message_count(db, session_id)
    if count >= MAX_MESSAGES_PER_SESSION:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Voce atingiu o limite de mensagens desta demonstracao",
        )


async def check_daily_budget(db: AsyncSession) -> None:
    result = await db.execute(
        select(func.coalesce(func.sum(DemoChatLog.total_tokens), 0)).where(
            DemoChatLog.created_at >= _today_start()
        )
    )
    used_today = result.scalar_one()
    if used_today >= settings.DEMO_DAILY_TOKEN_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demonstracao temporariamente indisponivel, tente novamente mais tarde",
        )


async def record_usage(db: AsyncSession, session_id: str, prompt_tokens: int, completion_tokens: int) -> None:
    db.add(
        DemoChatLog(
            session_id=session_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
    )
    await db.commit()
