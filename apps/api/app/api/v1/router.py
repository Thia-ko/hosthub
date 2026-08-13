from fastapi import APIRouter

from app.api.v1.routers import auth, health, instances, prompts

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(instances.router)
api_router.include_router(prompts.router)
