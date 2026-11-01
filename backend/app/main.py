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
from backend.app.db.session import init_db


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
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Allow all permissions as requested
        response.headers["Permissions-Policy"] = "geolocation=*, microphone=*, camera=*, display-capture=*, payment=*"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' https:; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:; "
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
