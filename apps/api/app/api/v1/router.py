from fastapi import APIRouter

from app.api.v1.routers import (
    ai_assist,
    ai_settings,
    analytics,
    auth,
    campaigns,
    conversations,
    dashboard,
    health,
    instance_members,
    instances,
    outbound_webhooks,
    prompt_templates,
    prompts,
    theme,
    webhook_events,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(instance_members.router)
api_router.include_router(prompts.router)
api_router.include_router(ai_assist.router)
api_router.include_router(webhook_events.router)
api_router.include_router(conversations.router)
api_router.include_router(dashboard.router)
api_router.include_router(dashboard.admin_router)
api_router.include_router(prompt_templates.router)
api_router.include_router(theme.router)
api_router.include_router(ai_settings.router)
api_router.include_router(analytics.router)
api_router.include_router(outbound_webhooks.router)
api_router.include_router(campaigns.router)
