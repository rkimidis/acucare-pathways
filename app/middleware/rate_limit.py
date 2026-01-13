"""Rate limiting middleware for security-critical endpoints.

Implements rate limiting to prevent:
- Brute force login attempts
- Magic link enumeration
- Intake submission spam
- API abuse

Uses in-memory storage by default. For production with multiple workers,
configure Redis backend via RATE_LIMIT_STORAGE_URL environment variable.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for a rate limit rule."""

    requests: int  # Number of allowed requests
    window_seconds: int  # Time window in seconds
    key_func: Callable[[Request], str] | None = None  # Custom key function

    @property
    def window_minutes(self) -> float:
        return self.window_seconds / 60


@dataclass
class RateLimitEntry:
    """Tracking entry for rate limit state."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


# Default rate limits by endpoint pattern
DEFAULT_RATE_LIMITS: dict[tuple[str, str], RateLimitConfig] = {
    # Authentication endpoints - strict limits
    ("POST", "/api/v1/auth/staff/login"): RateLimitConfig(
        requests=5, window_seconds=60
    ),
    ("POST", "/api/v1/auth/patient/request-magic-link"): RateLimitConfig(
        requests=3, window_seconds=60
    ),
    ("POST", "/api/v1/auth/patient/login"): RateLimitConfig(
        requests=10, window_seconds=60
    ),
    ("POST", "/api/v1/auth/staff/mfa/verify"): RateLimitConfig(
        requests=5, window_seconds=60
    ),
    # Intake endpoints - moderate limits
    ("POST", "/api/v1/intake/submit"): RateLimitConfig(
        requests=10, window_seconds=3600  # 10 per hour
    ),
    ("POST", "/api/v1/intake/draft"): RateLimitConfig(
        requests=60, window_seconds=3600  # 60 per hour
    ),
    # Check-in endpoints
    ("POST", "/api/v1/monitoring/patient/checkin/{checkin_id}"): RateLimitConfig(
        requests=10, window_seconds=3600
    ),
    # Booking endpoints
    ("POST", "/api/v1/scheduling/patient/appointments"): RateLimitConfig(
        requests=10, window_seconds=3600
    ),
}


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.

    Handles X-Forwarded-For header for reverse proxy scenarios.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain (original client)
        return forwarded.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


def normalize_path(path: str) -> str:
    """Normalize path by replacing UUIDs with placeholders."""
    import re

    # Replace UUID patterns with {id}
    uuid_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    normalized = re.sub(uuid_pattern, "{id}", path, flags=re.IGNORECASE)

    return normalized


class InMemoryRateLimitStorage:
    """In-memory rate limit storage.

    For single-worker deployments or development.
    For production with multiple workers, use Redis backend.
    """

    def __init__(self) -> None:
        self._storage: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes

    def _cleanup_expired(self, max_window: int = 3600) -> None:
        """Remove expired entries to prevent memory growth."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = [
            key
            for key, entry in self._storage.items()
            if now - entry.window_start > max_window
        ]

        for key in expired_keys:
            del self._storage[key]

        self._last_cleanup = now

    def check_and_increment(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check rate limit and increment counter.

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_seconds)
        """
        self._cleanup_expired()

        now = time.time()
        entry = self._storage[key]

        # Check if window has expired
        if now - entry.window_start > window_seconds:
            # Reset window
            entry.count = 1
            entry.window_start = now
            return True, limit - 1, window_seconds

        # Check if under limit
        if entry.count < limit:
            entry.count += 1
            remaining = limit - entry.count
            reset = int(window_seconds - (now - entry.window_start))
            return True, remaining, reset

        # Rate limited
        reset = int(window_seconds - (now - entry.window_start))
        return False, 0, reset


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI.

    Applies rate limits to configured endpoints based on client IP.
    Returns 429 Too Many Requests when limits are exceeded.
    """

    def __init__(
        self,
        app,
        rate_limits: dict[tuple[str, str], RateLimitConfig] | None = None,
        storage=None,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        self.rate_limits = rate_limits or DEFAULT_RATE_LIMITS
        self.storage = storage or InMemoryRateLimitStorage()
        self.enabled = enabled

    def _get_rate_limit_config(
        self, method: str, path: str
    ) -> RateLimitConfig | None:
        """Get rate limit configuration for a method/path combination."""
        normalized_path = normalize_path(path)

        # Direct match
        key = (method, path)
        if key in self.rate_limits:
            return self.rate_limits[key]

        # Normalized match
        key = (method, normalized_path)
        if key in self.rate_limits:
            return self.rate_limits[key]

        # Pattern match (for paths with {id} placeholders)
        for (cfg_method, cfg_path), config in self.rate_limits.items():
            if cfg_method != method:
                continue

            # Convert config path pattern to match normalized path
            if "{" in cfg_path:
                # Replace {param} with regex pattern
                import re

                pattern = cfg_path.replace("{checkin_id}", "{id}")
                pattern = pattern.replace("{id}", "[^/]+")
                pattern = f"^{pattern}$"
                if re.match(pattern, normalized_path):
                    return config

        return None

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and apply rate limiting."""
        if not self.enabled:
            return await call_next(request)

        method = request.method
        path = request.url.path

        # Get rate limit config for this endpoint
        config = self._get_rate_limit_config(method, path)

        if not config:
            # No rate limit configured for this endpoint
            return await call_next(request)

        # Generate rate limit key
        client_ip = get_client_ip(request)
        if config.key_func:
            key = config.key_func(request)
        else:
            key = f"{method}:{path}:{client_ip}"

        # Check rate limit
        is_allowed, remaining, reset = self.storage.check_and_increment(
            key, config.requests, config.window_seconds
        )

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded: {method} {path} from {client_ip}"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": reset,
                },
                headers={
                    "Retry-After": str(reset),
                    "X-RateLimit-Limit": str(config.requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset),
                },
            )

        # Process request normally
        response = await call_next(request)

        # Add rate limit headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)

        return response


# Redis-based storage for production (multi-worker deployments)
class RedisRateLimitStorage:
    """Redis-based rate limit storage for production.

    Use this when running multiple API workers behind a load balancer.
    Requires redis-py package.
    """

    def __init__(self, redis_url: str) -> None:
        try:
            import redis

            self.redis = redis.from_url(redis_url)
        except ImportError:
            raise ImportError(
                "redis package required for Redis rate limit storage. "
                "Install with: pip install redis"
            )

    def check_and_increment(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        """Check rate limit using Redis with sliding window."""
        import time

        now = int(time.time())
        window_key = f"ratelimit:{key}:{now // window_seconds}"

        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds)
        results = pipe.execute()

        current_count = results[0]

        if current_count <= limit:
            remaining = limit - current_count
            reset = window_seconds - (now % window_seconds)
            return True, remaining, reset

        reset = window_seconds - (now % window_seconds)
        return False, 0, reset
