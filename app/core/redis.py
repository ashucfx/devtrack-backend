import json
import logging
import uuid
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Enterprise Async Redis Client and Cache Manager with resilient fallback."""

    def __init__(self) -> None:
        self._pool: ConnectionPool | None = None
        self._client: aioredis.Redis | None = None

    def initialize(self) -> None:
        """Initialize connection pool using configured settings."""
        settings = get_settings()
        if not self._pool:
            self._pool = ConnectionPool.from_url(
                settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
            )
            self._client = aioredis.Redis(connection_pool=self._pool)

    @property
    def client(self) -> aioredis.Redis | None:
        """Return the initialized async redis client."""
        if self._client is None:
            self.initialize()
        return self._client

    def set_client(self, client: aioredis.Redis | None) -> None:
        """Override the Redis client (useful for unit testing with mocks or fakeredis)."""
        self._client = client

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        try:
            if self.client:
                return await self.client.ping()
        except Exception as e:
            logger.warning("Redis ping failed: %s", e)
        return False

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Retrieve and deserialize a JSON payload from Redis."""
        try:
            if self.client:
                raw = await self.client.get(key)
                if raw:
                    return json.loads(raw)
        except Exception as e:
            logger.warning("Failed to retrieve cache key '%s' from Redis: %s", key, e)
        return None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int = 300) -> bool:
        """Serialize and store a JSON payload with TTL."""
        try:
            if self.client:
                serialized = json.dumps(value)
                await self.client.set(key, serialized, ex=ttl_seconds)
                return True
        except Exception as e:
            logger.warning("Failed to write cache key '%s' to Redis: %s", key, e)
        return False

    async def delete(self, key: str) -> bool:
        """Delete a single key from Redis."""
        try:
            if self.client:
                await self.client.delete(key)
                return True
        except Exception as e:
            logger.warning("Failed to delete cache key '%s' from Redis: %s", key, e)
        return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern using SCAN to avoid blocking."""
        deleted_count = 0
        try:
            if self.client:
                cursor = 0
                while True:
                    cursor, keys = await self.client.scan(cursor=cursor, match=pattern, count=100)
                    if keys:
                        deleted = await self.client.delete(*keys)
                        deleted_count += deleted
                    if cursor == 0:
                        break
        except Exception as e:
            logger.warning("Failed to delete cache pattern '%s' from Redis: %s", pattern, e)
        return deleted_count

    async def close(self) -> None:
        """Close connection pool cleanly during application shutdown."""
        if self._client:
            await self._client.aclose()
        if self._pool:
            await self._pool.disconnect()
        self._client = None
        self._pool = None

    @staticmethod
    def dashboard_cache_key(user_id: uuid.UUID) -> str:
        """Generate standardized cache key for user dashboard KPIs."""
        return f"devtrack:cache:dashboard:{user_id}"

    @staticmethod
    def ratelimit_key(prefix: str, identifier: str) -> str:
        """Generate standardized rate limit key."""
        return f"devtrack:ratelimit:{prefix}:{identifier}"


redis_manager = RedisManager()


async def get_redis_client() -> aioredis.Redis | None:
    """FastAPI dependency for accessing the Redis client."""
    return redis_manager.client
