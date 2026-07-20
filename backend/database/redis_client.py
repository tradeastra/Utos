"""
Async Redis client for UTOS Trading Engine.

Uses redis.asyncio (bundled with redis-py >= 4.2).
Initialised in app lifespan; health-checked via ping().
"""

import json
from typing import Any

import redis.asyncio as aioredis
from core.config import get_redis_url
from core.logging import get_logger

logger = get_logger(__name__)

_redis: aioredis.Redis | None = None  # type: ignore[type-arg]


async def init_redis(redis_url: str | None = None) -> aioredis.Redis:  # type: ignore[type-arg]
    """Create the async Redis connection pool and verify connectivity."""
    global _redis
    url = redis_url or get_redis_url()
    _redis = aioredis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    try:
        await _redis.ping()
        logger.info("Redis connected", extra={"url": url})
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Redis ping failed — continuing without cache", extra={"error": str(exc)}
        )
    return _redis


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("Redis connection closed")


def get_redis() -> aioredis.Redis | None:  # type: ignore[type-arg]
    """Return the active Redis client (None if not yet initialised)."""
    return _redis


async def redis_ping() -> bool:
    """Return True if Redis is reachable."""
    client = get_redis()
    if client is None:
        return False
    try:
        return await client.ping()  # type: ignore[return-value]
    except Exception:  # noqa: BLE001
        return False


class RedisCache:
    """Redis cache wrapper with utility methods."""

    def __init__(self, prefix: str = "utos"):
        self.redis = get_redis()
        self.prefix = prefix

    def _make_key(self, key: str) -> str:
        """Create prefixed key."""
        return f"{self.prefix}:{key}"

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set a key-value pair with optional TTL."""
        try:
            full_key = self._make_key(key)
            serialized_value = json.dumps(value, default=str)

            if ttl:
                return self.redis.setex(full_key, ttl, serialized_value)
            else:
                return self.redis.set(full_key, serialized_value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def get(self, key: str) -> Any | None:
        """Get a value by key."""
        try:
            full_key = self._make_key(key)
            value = self.redis.get(full_key)

            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def delete(self, key: str) -> bool:
        """Delete a key."""
        try:
            full_key = self._make_key(key)
            return bool(self.redis.delete(full_key))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            full_key = self._make_key(key)
            return bool(self.redis.exists(full_key))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for a key."""
        try:
            full_key = self._make_key(key)
            return bool(self.redis.expire(full_key, ttl))
        except Exception as e:
            logger.error(f"Redis expire error: {e}")
            return False

    def ttl(self, key: str) -> int:
        """Get TTL for a key."""
        try:
            full_key = self._make_key(key)
            return self.redis.ttl(full_key)
        except Exception as e:
            logger.error(f"Redis ttl error: {e}")
            return -1

    def increment(self, key: str, amount: int = 1) -> int | None:
        """Increment a numeric value."""
        try:
            full_key = self._make_key(key)
            return self.redis.incrby(full_key, amount)
        except Exception as e:
            logger.error(f"Redis increment error: {e}")
            return None

    def decrement(self, key: str, amount: int = 1) -> int | None:
        """Decrement a numeric value."""
        try:
            full_key = self._make_key(key)
            return self.redis.decrby(full_key, amount)
        except Exception as e:
            logger.error(f"Redis decrement error: {e}")
            return None

    def hset(self, key: str, field: str, value: Any) -> bool:
        """Set a hash field."""
        try:
            full_key = self._make_key(key)
            serialized_value = json.dumps(value, default=str)
            return bool(self.redis.hset(full_key, field, serialized_value))
        except Exception as e:
            logger.error(f"Redis hset error: {e}")
            return False

    def hget(self, key: str, field: str) -> Any | None:
        """Get a hash field."""
        try:
            full_key = self._make_key(key)
            value = self.redis.hget(full_key, field)

            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis hget error: {e}")
            return None

    def hgetall(self, key: str) -> dict:
        """Get all hash fields."""
        try:
            full_key = self._make_key(key)
            data = self.redis.hgetall(full_key)

            result = {}
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except json.JSONDecodeError:
                    result[field] = value

            return result
        except Exception as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}

    def hdel(self, key: str, field: str) -> bool:
        """Delete a hash field."""
        try:
            full_key = self._make_key(key)
            return bool(self.redis.hdel(full_key, field))
        except Exception as e:
            logger.error(f"Redis hdel error: {e}")
            return False

    def lpush(self, key: str, *values: Any) -> int | None:
        """Push values to the left of a list."""
        try:
            full_key = self._make_key(key)
            serialized_values = [json.dumps(v, default=str) for v in values]
            return self.redis.lpush(full_key, *serialized_values)
        except Exception as e:
            logger.error(f"Redis lpush error: {e}")
            return None

    def rpush(self, key: str, *values: Any) -> int | None:
        """Push values to the right of a list."""
        try:
            full_key = self._make_key(key)
            serialized_values = [json.dumps(v, default=str) for v in values]
            return self.redis.rpush(full_key, *serialized_values)
        except Exception as e:
            logger.error(f"Redis rpush error: {e}")
            return None

    def lpop(self, key: str) -> Any | None:
        """Pop value from the left of a list."""
        try:
            full_key = self._make_key(key)
            value = self.redis.lpop(full_key)

            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis lpop error: {e}")
            return None

    def rpop(self, key: str) -> Any | None:
        """Pop value from the right of a list."""
        try:
            full_key = self._make_key(key)
            value = self.redis.rpop(full_key)

            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis rpop error: {e}")
            return None

    def lrange(self, key: str, start: int = 0, end: int = -1) -> list[Any]:
        """Get range of list values."""
        try:
            full_key = self._make_key(key)
            values = self.redis.lrange(full_key, start, end)

            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except json.JSONDecodeError:
                    result.append(value)

            return result
        except Exception as e:
            logger.error(f"Redis lrange error: {e}")
            return []

    def llen(self, key: str) -> int:
        """Get list length."""
        try:
            full_key = self._make_key(key)
            return self.redis.llen(full_key)
        except Exception as e:
            logger.error(f"Redis llen error: {e}")
            return 0

    def publish(self, channel: str, message: Any) -> int:
        """Publish a message to a channel."""
        try:
            serialized_message = json.dumps(message, default=str)
            return self.redis.publish(channel, serialized_message)
        except Exception as e:
            logger.error(f"Redis publish error: {e}")
            return 0

    def subscribe(self, channel: str) -> Any:
        """Subscribe to a channel."""
        try:
            pubsub = self.redis.pubsub()
            pubsub.subscribe(channel)
            return pubsub
        except Exception as e:
            logger.error(f"Redis subscribe error: {e}")
            raise

    def health_check(self) -> bool:
        """Check Redis health."""
        try:
            return self.redis.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Create default cache instance
cache = RedisCache()
