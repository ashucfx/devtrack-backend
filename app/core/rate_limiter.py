import logging
import time

from fastapi import Request

from app.core.exceptions import RateLimitExceededException
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window log rate limiter backed by Redis with resilient fallback."""

    def __init__(
        self,
        max_requests: int = 5,
        window_seconds: int = 60,
        key_prefix: str = "general",
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix

    async def __call__(self, request: Request) -> None:
        """Evaluate rate limit for incoming client request."""
        # Extract client identifier
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        elif request.client and request.client.host:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"

        key = redis_manager.ratelimit_key(self.key_prefix, client_ip)
        now = time.time()
        window_start = now - self.window_seconds

        client = redis_manager.client
        if client is None:
            # Fallback if Redis is unavailable
            return

        try:
            # Pipeline sliding window commands atomically
            async with client.pipeline(transaction=True) as pipe:
                # Remove timestamps older than current window
                pipe.zremrangebyscore(key, 0, window_start)
                # Add current request timestamp
                pipe.zadd(key, {f"{now}:{time.perf_counter()}": now})
                # Count total requests in active window
                pipe.zcard(key)
                # Set key expiry to ensure TTL cleanup
                pipe.expire(key, self.window_seconds + 5)
                results = await pipe.execute()

            request_count = results[2]
            if request_count > self.max_requests:
                logger.warning(
                    "Rate limit exceeded for IP %s on '%s' (%d/%d reqs in %ds)",
                    client_ip,
                    self.key_prefix,
                    request_count,
                    self.max_requests,
                    self.window_seconds,
                )
                raise RateLimitExceededException(retry_after_seconds=self.window_seconds)
        except RateLimitExceededException:
            raise
        except Exception as e:
            logger.warning("Rate limiter Redis operation error: %s. Allowing request.", e)
