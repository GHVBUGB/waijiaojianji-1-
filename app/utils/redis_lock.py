import asyncio
import time
import uuid
from typing import Optional

try:
    import redis.asyncio as redis
except Exception:  # pragma: no cover
    redis = None  # type: ignore


class RedisAsyncLock:
    """
    Simple async distributed lock using Redis SET NX PX + value check on release.
    Designed for short critical sections (e.g., ASR) across serverless instances.
    """

    def __init__(
        self,
        redis_url: Optional[str],
        key: str,
        ttl_ms: int = 15 * 60 * 1000,
        retry_interval_ms: int = 500,
        max_wait_ms: int = 10 * 60 * 1000,
    ) -> None:
        self.redis_url = redis_url
        self.key = key
        self.ttl_ms = ttl_ms
        self.retry_interval_ms = retry_interval_ms
        self.max_wait_ms = max_wait_ms
        self._client: Optional["redis.Redis"] = None
        self._token: str = uuid.uuid4().hex

    async def __aenter__(self):
        if not self.redis_url or not redis:
            # No Redis available; behave as no-op lock
            return self
        self._client = redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        start = time.monotonic() * 1000
        while True:
            acquired = await self._client.set(self.key, self._token, nx=True, px=self.ttl_ms)
            if acquired:
                return self
            if (time.monotonic() * 1000) - start > self.max_wait_ms:
                raise TimeoutError("Timed out waiting for global ASR lock")
            await asyncio.sleep(self.retry_interval_ms / 1000.0)

    async def __aexit__(self, exc_type, exc, tb):
        if not self._client:
            return False
        # Release only if value matches (avoid unlocking others)
        lua = (
            "if redis.call('get', KEYS[1]) == ARGV[1] then "
            "return redis.call('del', KEYS[1]) else return 0 end"
        )
        try:
            await self._client.eval(lua, 1, self.key, self._token)
        finally:
            await self._client.close()
        return False
