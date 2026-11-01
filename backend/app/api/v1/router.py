"""Version 1 API router."""

from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.documents import router as documents_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.escalations import router as escalations_router

api_v1_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(documents_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(escalations_router)

