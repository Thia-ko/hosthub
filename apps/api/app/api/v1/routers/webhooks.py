from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.instance import Instance
from app.models.webhook_event import WebhookEvent

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_EXCLUDED_HEADERS = {"cookie", "authorization", "host", "connection", "content-length"}


@router.post("/{webhook_token}")
async def receive_webhook(webhook_token: str, request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Instance).where(Instance.webhook_token == webhook_token))
    instance = result.scalar_one_or_none()
    if instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instancia nao encontrada")

    raw_body = await request.body()
    try:
        payload = await request.json() if raw_body else {}
    except ValueError:
        payload = {"_raw": raw_body.decode("utf-8", errors="replace")}

    headers = {key: value for key, value in request.headers.items() if key.lower() not in _EXCLUDED_HEADERS}

    db.add(WebhookEvent(instance_id=instance.id, headers_json=headers, payload_json=payload))
    await db.commit()

    return {"received": True}
