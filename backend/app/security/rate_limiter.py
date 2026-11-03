"""Redis-backed distributed sliding window rate limiter with resilient in-memory fallback.

Supports multiple uvicorn/gunicorn workers safely via Redis sorted sets.
Gracefully degrades to thread-safe in-memory tracking if Redis is unreachable.
"""

from collections import defaultdict
import logging
import threading
import time
from typing import Dict, List, Optional
import uuid
from fastapi import HTTPException, Request, status

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


class DistributedRateLimiter:
    """
    Sliding window rate limiter utilizing Redis with transparent in-memory fallback.
    """

    def __init__(self):
        self._redis_client = None
        self._redis_checked = False
        self._memory_lock = threading.Lock()
        self._memory_store: Dict[str, List[float]] = defaultdict(list)

    def _get_redis(self):
        """Lazy initialization of Redis connection."""
        if not self._redis_checked:
            settings = get_settings()
            if settings.REDIS_URL:
                try:
                    import redis
                    client = redis.from_url(
                        settings.REDIS_URL,
                        socket_timeout=1.5,
                        socket_connect_timeout=1.5,
                        decode_responses=True,
                    )
                    # Verify connectivity
                    client.ping()
                    self._redis_client = client
                    logger.info("Distributed rate limiter initialized with Redis at %s", settings.REDIS_URL)
                except Exception as exc:
                    logger.warning("Redis unavailable for rate limiting (%s). Falling back to in-memory rate limiting.", exc)
                    self._redis_client = None
            self._redis_checked = True
        return self._redis_client

    def _check_redis(self, redis_conn, key: str, limit: int, window: float) -> bool:
        """Execute sliding window check via Redis sorted sets."""
        now = time.time()
        window_start = now - window
        member_id = f"{now}:{uuid.uuid4().hex[:6]}"

        try:
            pipe = redis_conn.pipeline()
            # 1. Remove expired entries older than the window
            pipe.zremrangebyscore(key, 0, window_start)
            # 2. Count current hits within the window
            pipe.zcard(key)
            results = pipe.execute()
            current_count = results[1]

            if current_count >= limit:
                return False

            # 3. Add current request and refresh TTL
            pipe = redis_conn.pipeline()
            pipe.zadd(key, {member_id: now})
            pipe.expire(key, int(window) + 5)
            pipe.execute()
            return True
        except Exception as exc:
            logger.warning("Redis rate limit operation failed (%s). Falling back to memory.", exc)
            return self._check_memory(key, limit, window)

    def _check_memory(self, key: str, limit: int, window: float) -> bool:
        """Thread-safe in-memory sliding window check."""
        now = time.time()
        window_start = now - window

        with self._memory_lock:
            history = self._memory_store[key]
            # Purge entries outside window
            valid_history = [ts for ts in history if ts > window_start]
            if len(valid_history) >= limit:
                self._memory_store[key] = valid_history
                return False

            valid_history.append(now)
            self._memory_store[key] = valid_history
            return True

    def check(self, request: Request, scope: str = "general", max_requests: Optional[int] = None, window_seconds: float = 60.0):
        """
        Check rate limit for client IP. Raises HTTP 429 if limit is reached.
        """
        settings = get_settings()
        limit = max_requests if max_requests is not None else settings.RATE_LIMIT_PER_MINUTE
        client_ip = request.client.host if request.client else "127.0.0.1"
        key = f"rl:{scope}:{client_ip}"

        redis_conn = self._get_redis()
        allowed = (
            self._check_redis(redis_conn, key, limit, window_seconds)
            if redis_conn
            else self._check_memory(key, limit, window_seconds)
        )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {scope}. Maximum {limit} requests per {int(window_seconds)}s allowed.",
            )


# Global singleton instance
_limiter = DistributedRateLimiter()


def get_rate_limiter() -> DistributedRateLimiter:
    """Return singleton instance of the distributed rate limiter."""
    return _limiter


def rate_limit_guard(request: Request):
    """General API rate limit guard (30 req/min)."""
    _limiter.check(request, scope="chat")


def rate_limit_admin_guard(request: Request):
    """Strict admin endpoint rate limit guard (10 req/min)."""
    _limiter.check(request, scope="admin", max_requests=10)


def rate_limit_lead_guard(request: Request):
    """Lead and ticket creation rate limit guard (10 req/min)."""
    _limiter.check(request, scope="lead_ticket", max_requests=10)
