from fastapi import FastAPI

from app.api.v1.router import api_router
from app.api.v1.routers.webhooks import router as public_webhooks_router

app = FastAPI(title="Hosthub API")
app.include_router(api_router)
app.include_router(public_webhooks_router)
