"""In-memory sliding window rate limiter for API endpoints."""

import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status
from backend.app.config import get_settings


class SlidingWindowRateLimiter:
    """Sliding-window request rate limiter per client IP."""

    def __init__(self):
        self.settings = get_settings()
        self._history: Dict[str, List[float]] = defaultdict(list)

    def check(self, request: Request):
        limit = self.settings.RATE_LIMIT_PER_MINUTE
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window_start = now - 60.0

        # Purge timestamps older than 60s
        self._history[client_ip] = [ts for ts in self._history[client_ip] if ts > window_start]

        if len(self._history[client_ip]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
            )

        self._history[client_ip].append(now)


_rate_limiter = SlidingWindowRateLimiter()


def rate_limit_guard(request: Request):
    """FastAPI dependency to enforce rate limiting."""
    _rate_limiter.check(request)

