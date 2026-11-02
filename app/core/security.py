from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from redis.asyncio import Redis

from app.cache import get_redis, redis_client
from app.core.config import settings
from app.core.rate_limiter import SlidingWindowRateLimiter

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)
rate_limiter = SlidingWindowRateLimiter(
    redis_client,
    requests_limit=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


async def verify_api_key(
    api_key: str = Security(API_KEY_HEADER),
) -> str:
    valid_keys = {key.strip() for key in settings.API_KEYS.split(",") if key.strip()}
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key


async def rate_limit(
    api_key: str = Security(verify_api_key),
    _redis: Redis = Depends(get_redis),
) -> str:
    await rate_limiter.check(api_key)
    return api_key
