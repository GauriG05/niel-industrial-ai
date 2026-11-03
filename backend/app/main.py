"""FastAPI Application Entry Point for NIEL Industrial Intelligence AI."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.config import PROJECT_ROOT, get_settings
from backend.app.api.v1.router import api_v1_router
from backend.app.api.v1.ws_chat import router as ws_router
from backend.app.db.session import init_db, check_db_health
from backend.app.observability.logging_config import setup_logging
from backend.app.observability.metrics import get_metrics_collector
from backend.app.observability.middleware import ObservabilityMiddleware
from backend.app.security.rate_limiter import get_rate_limiter

# Initialize structured logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown hooks."""
    settings = get_settings()
    # Ensure data storage directories exist securely
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    settings.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject protective HTTP security headers into every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Restrict all sensitive hardware, location, and payment device permissions
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), display-capture=()"
        # Tightened Content Security Policy without unsafe-eval
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https:; "
            "style-src 'self' 'unsafe-inline' https:; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss: https: https://*.whatsapp.com https://*.wa.me; "
            "frame-ancestors 'self' https://newindiaelectricals.com https://www.newindiaelectricals.com;"
        )
        return response


settings = get_settings()

app = FastAPI(
    title="NIEL Industrial Intelligence AI API",
    description="Secure Generative AI & Retrieval-Augmented Generation API for New India Electricals Ltd.",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# Apply Observability Middleware (Request IDs, JSON Access Logs, Prometheus telemetry)
app.add_middleware(ObservabilityMiddleware)

# Apply Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Apply CORS with explicit allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Key", "X-Request-ID"],
)

# Mount embeddable widget static files directory
WIDGET_DIR = PROJECT_ROOT / "widget"
if WIDGET_DIR.is_dir():
    app.mount("/widget", StaticFiles(directory=str(WIDGET_DIR)), name="widget")

# Mount official PDFs directory for chat attachments and downloads
PDFS_DIR = PROJECT_ROOT / "PDFs"
if PDFS_DIR.is_dir():
    app.mount("/pdfs", StaticFiles(directory=str(PDFS_DIR)), name="pdfs")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Prevent unhandled internal stack traces from leaking to clients."""
    settings = get_settings()
    if settings.DEBUG:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": str(exc), "type": type(exc).__name__},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact the administrator."},
    )


# Mount versioned API routes
app.include_router(api_v1_router)
app.include_router(ws_router)


@app.get("/")
def root():
    """Service discovery root endpoint."""
    return {
        "service": "NIEL Industrial Intelligence AI",
        "version": "0.1.0",
        "status": "operational",
        "api_docs": "/docs" if settings.DEBUG else "disabled",
    }


@app.get("/health")
def health():
    """Comprehensive health check endpoint inspecting DB, cache, and service status."""
    db_ok = check_db_health()
    rl = get_rate_limiter()
    redis_conn = rl._get_redis()
    redis_ok = redis_conn is not None

    status_str = "healthy" if db_ok else "degraded"
    return {
        "status": status_str,
        "database": "connected" if db_ok else "unreachable",
        "redis_cache": "connected" if redis_ok else "in-memory-fallback",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/metrics")
def metrics():
    """Prometheus-compatible metrics exposition endpoint."""
    collector = get_metrics_collector()
    from starlette.responses import Response
    return Response(
        content=collector.render_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
