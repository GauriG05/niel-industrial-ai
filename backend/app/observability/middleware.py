"""FastAPI middleware for request correlation, structured access logging, and metrics."""

import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.app.observability.logging_config import current_request_id
from backend.app.observability.metrics import get_metrics_collector

logger = logging.getLogger("niel.access")


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Intercepts HTTP requests to assign correlation IDs and collect telemetry."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Resolve or generate request ID
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = current_request_id.set(req_id)

        start_time = time.perf_counter()
        status_code = 500

        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = req_id
            return response

        except Exception as exc:
            logger.error("Unhandled exception processing request: %s", exc, exc_info=True)
            raise

        finally:
            elapsed_sec = time.perf_counter() - start_time
            elapsed_ms = elapsed_sec * 1000

            # Record Prometheus metrics
            metrics = get_metrics_collector()
            metrics.record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_sec=elapsed_sec,
            )

            # Skip logging healthcheck spam
            if request.url.path not in {"/health", "/metrics", "/favicon.ico"}:
                logger.info(
                    "HTTP %s %s -> %d in %.2fms",
                    request.method,
                    request.url.path,
                    status_code,
                    elapsed_ms,
                    extra={
                        "http_method": request.method,
                        "http_path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": round(elapsed_ms, 2),
                        "client_ip": request.client.host if request.client else "unknown",
                    },
                )

            current_request_id.reset(token)
