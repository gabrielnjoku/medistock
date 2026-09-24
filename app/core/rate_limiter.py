import time
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request, status

from app.core.cache import get_redis_client

# In-memory store for rate limiting when Redis is unavailable
_memory_rate_limit: Dict[str, List[float]] = {}


def reset_rate_limits() -> None:
    """Reset rate limiter memory state (useful for test suites)."""
    global _memory_rate_limit
    _memory_rate_limit.clear()


class RateLimiter:
    """FastAPI Dependency factory enforcing sliding-window rate limits per client IP.

    Usage:
      Depends(RateLimiter(key_prefix="login", requests_limit=5, window_seconds=60))
    """

    def __init__(self, key_prefix: str, requests_limit: int, window_seconds: int = 60):
        self.key_prefix = key_prefix
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds

    def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        key = f"rate_limit:{self.key_prefix}:{client_ip}"
        now = time.time()

        r = get_redis_client()
        if r is not None:
            try:
                # Redis sliding-window using ZSET
                pipeline = r.pipeline()
                pipeline.zremrangebyscore(key, 0, now - self.window_seconds)
                pipeline.zadd(key, {str(now): now})
                pipeline.zcard(key)
                pipeline.expire(key, self.window_seconds)
                _, _, req_count, _ = pipeline.execute()

                if req_count > self.requests_limit:
                    oldest_entries = r.zrange(key, 0, 0, withscores=True)
                    oldest_ts = oldest_entries[0][1] if oldest_entries else now
                    retry_after = max(1, int(self.window_seconds - (now - oldest_ts)))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                        headers={"Retry-After": str(retry_after)},
                    )
                return
            except HTTPException:
                raise
            except Exception:
                pass  # Fall through to in-memory check if Redis pipeline fails

        # In-memory sliding-window fallback
        timestamps = _memory_rate_limit.get(key, [])
        valid_timestamps = [ts for ts in timestamps if now - ts < self.window_seconds]

        if len(valid_timestamps) >= self.requests_limit:
            oldest_ts = valid_timestamps[0]
            retry_after = max(1, int(self.window_seconds - (now - oldest_ts)))
            _memory_rate_limit[key] = valid_timestamps
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        valid_timestamps.append(now)
        _memory_rate_limit[key] = valid_timestamps
