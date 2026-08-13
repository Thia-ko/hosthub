import httpx

from app.core.config import settings

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str | None) -> bool:
    if not settings.TURNSTILE_SECRET_KEY:
        return True
    if not token:
        return False

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            SITEVERIFY_URL, data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token}
        )
    return bool(response.json().get("success"))
