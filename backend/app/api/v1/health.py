"""Health check and readiness endpoints."""

from fastapi import APIRouter, Depends
from backend.app.config import Settings, get_settings
from backend.app.schemas.common import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
def get_health(settings: Settings = Depends(get_settings)):
    """Return application health, current environment, and service status."""
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        version="0.1.0",
        kill_switch_active=settings.KILL_SWITCH_ENABLED,
    )


@router.get("/ready")
def get_ready(settings: Settings = Depends(get_settings)):
    """Check application readiness."""
    data_dir_ready = settings.DATA_DIR.exists()
    return {
        "status": "ready" if data_dir_ready else "initializing",
        "data_dir_accessible": data_dir_ready,
    }

