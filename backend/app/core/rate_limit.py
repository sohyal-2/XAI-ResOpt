"""Sliding window rate limiter using Redis sorted sets."""

import logging
import time
from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import get_settings
from app.services.redis import get_redis

logger = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window rate limiter powered by Redis sorted sets.

    Tracks request timestamps within a given time window. If the count exceeds
    the limit, returns HTTP 429 with standard Retry-After header.
    """

    def __init__(self, times: int, seconds: int, key_prefix: str = "rate_limit") -> None:
        self.times = times
        self.seconds = seconds
        self.key_prefix = key_prefix

    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(get_redis),
    ) -> None:
        settings = get_settings()
        if getattr(settings, "disable_rate_limiting", False):
            return

        # Determine client identifier
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            client_id = f"token:{abs(hash(auth_header))}"
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            client_id = f"ip:{client_ip}"

        redis_key = f"{self.key_prefix}:{client_id}"
        now = time.time()
        window_start = now - self.seconds

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            results = await pipe.execute()

            current_count = results[1]
            if current_count >= self.times:
                retry_after = max(1, int(self.seconds))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: maximum {self.times} requests per {self.seconds} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            # Record this request
            entry_id = f"{now}:{time.time_ns()}"
            pipe = redis.pipeline()
            pipe.zadd(redis_key, {entry_id: now})
            pipe.expire(redis_key, self.seconds + 5)
            await pipe.execute()

        except HTTPException:
            raise
        except Exception as exc:
            # If Redis check fails unexpectedly, fail-open to preserve availability
            logger.warning(f"Rate limiting check error: {exc}")
