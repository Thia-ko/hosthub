from fastapi import APIRouter

from app.api.v1.routers import ai_assist, auth, dashboard, health, instances, prompt_templates, prompts, webhook_events

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(prompts.router)
api_router.include_router(ai_assist.router)
api_router.include_router(webhook_events.router)
api_router.include_router(dashboard.router)
api_router.include_router(prompt_templates.router)
