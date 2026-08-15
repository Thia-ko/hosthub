import asyncio
import contextlib

from fastapi import FastAPI

from app.api.v1.router import api_router
from app.api.v1.routers.webhooks import router as public_webhooks_router
from app.services.scheduler import run_auto_generation_scheduler


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(run_auto_generation_scheduler())
    try:
        yield
    finally:
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task


app = FastAPI(title="Hosthub API", lifespan=lifespan)
app.include_router(api_router)
app.include_router(public_webhooks_router)
