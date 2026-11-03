"""Version 1 API router."""

from fastapi import APIRouter
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.chat import router as chat_router
from backend.app.api.v1.escalations import router as escalations_router
from backend.app.api.v1.customers import router as customers_router
from backend.app.api.v1.leads import router as leads_router
from backend.app.api.v1.tickets import router as tickets_router
from backend.app.api.v1.flagged_queries import router as flagged_queries_router
from backend.app.api.v1.session_auth import router as session_auth_router

api_v1_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(session_auth_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(escalations_router)
api_v1_router.include_router(customers_router)
api_v1_router.include_router(leads_router)
api_v1_router.include_router(tickets_router)
api_v1_router.include_router(flagged_queries_router)

