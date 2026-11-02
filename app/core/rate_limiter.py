import time
import uuid

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import NoScriptError

SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local clear_before = now - window

redis.call('ZREMRANGEBYSCORE', key, 0, clear_before)
local current_requests = redis.call('ZCARD', key)

if current_requests >= limit then
    return 0
end

redis.call('ZADD', key, now, ARGV[4])
redis.call('EXPIRE', key, math.ceil(window / 1000))
return 1
"""


class SlidingWindowRateLimiter:
    def __init__(
        self,
        redis: Redis,
        requests_limit: int,
        window_seconds: int,
        key_prefix: str = "rate_limit",
    ) -> None:
        if requests_limit < 1 or window_seconds < 1:
            raise ValueError("Rate-limit values must be positive")
        self.redis = redis
        self.requests_limit = requests_limit
        self.window_ms = window_seconds * 1000
        self.key_prefix = key_prefix
        self._script_sha: str | None = None

    async def check(self, identifier: str) -> None:
        now_ms = int(time.time() * 1000)
        key = f"{self.key_prefix}:{identifier}"
        member = f"{now_ms}:{uuid.uuid4()}"

        if self._script_sha is None:
            self._script_sha = await self.redis.script_load(SLIDING_WINDOW_LUA)

        try:
            allowed = await self.redis.evalsha(
                self._script_sha,
                1,
                key,
                now_ms,
                self.window_ms,
                self.requests_limit,
                member,
            )
        except NoScriptError:
            self._script_sha = await self.redis.script_load(SLIDING_WINDOW_LUA)
            allowed = await self.redis.evalsha(
                self._script_sha,
                1,
                key,
                now_ms,
                self.window_ms,
                self.requests_limit,
                member,
            )

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please throttle requests.",
                headers={"Retry-After": str(self.window_ms // 1000)},
            )
