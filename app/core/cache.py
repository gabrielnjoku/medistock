import fnmatch
import logging
import time
from typing import Dict, Optional, Tuple
import redis

from app.core.config import get_settings

logger = logging.getLogger("medistock.cache")
settings = get_settings()

_redis_client: Optional[redis.Redis] = None
_redis_disabled: bool = False
_memory_cache: Dict[str, Tuple[str, float]] = {}


def get_redis_client() -> Optional[redis.Redis]:
    """Retrieves or initializes a Redis client connection.

    Falls back to in-memory cache if Redis is unavailable or un-reachable.
    """
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_connect_timeout=0.2)
        r.ping()
        _redis_client = r
        logger.info("Connected to Redis server successfully.")
        return _redis_client
    except Exception as exc:
        logger.debug(f"Redis unavailable ({exc}), using in-memory cache fallback.")
        _redis_disabled = True
        return None


def get_cache(key: str) -> Optional[str]:
    """Retrieve string value for a cache key."""
    r = get_redis_client()
    if r is not None:
        try:
            return r.get(key)
        except Exception as exc:
            logger.warning(f"Redis get failed: {exc}")

    # Fallback to in-memory store
    now = time.time()
    if key in _memory_cache:
        val, expiry = _memory_cache[key]
        if expiry > now:
            return val
        else:
            del _memory_cache[key]
    return None


def set_cache(key: str, value: str, expire_seconds: int = 300) -> None:
    """Store string value for a cache key with a Time-To-Live (TTL) expiration."""
    r = get_redis_client()
    if r is not None:
        try:
            r.setex(key, expire_seconds, value)
            return
        except Exception as exc:
            logger.warning(f"Redis setex failed: {exc}")

    # Fallback to in-memory store
    _memory_cache[key] = (value, time.time() + expire_seconds)


def invalidate_cache_pattern(pattern: str) -> int:
    """Invalidate all keys matching a glob pattern (e.g. 'cache:inventory:*').

    Ensures read consistency when write operations mutate database state.
    """
    invalidated_count = 0
    r = get_redis_client()
    if r is not None:
        try:
            keys = r.keys(pattern)
            if keys:
                invalidated_count += r.delete(*keys)
        except Exception as exc:
            logger.warning(f"Redis pattern invalidation failed: {exc}")

    # Invalidate in-memory store matching pattern
    keys_to_del = [k for k in _memory_cache if fnmatch.fnmatch(k, pattern)]
    for k in keys_to_del:
        _memory_cache.pop(k, None)
        invalidated_count += 1

    logger.debug(f"Invalidated {invalidated_count} cache keys for pattern: {pattern}")
    return invalidated_count


def clear_all_cache() -> None:
    """Clear all cached entries (useful for test setup/teardown)."""
    global _memory_cache
    _memory_cache.clear()
    r = get_redis_client()
    if r is not None:
        try:
            r.flushdb()
        except Exception:
            pass
