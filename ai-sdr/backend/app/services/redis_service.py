import time
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RedisService:
    def __init__(self):
        self._client: Optional[object] = None
        self._upstash_url: Optional[str] = None
        self._upstash_token: Optional[str] = None
        self._in_memory: dict[str, list[float]] = {}
        self._mode: str = "memory"

    async def initialize(
        self,
        upstash_url: str = "",
        upstash_token: str = "",
        redis_url: str = "",
    ):
        if upstash_url and upstash_token:
            self._upstash_url = upstash_url.rstrip("/")
            self._upstash_token = upstash_token
            self._mode = "upstash"
            logger.info("Redis: using Upstash")
        elif redis_url:
            try:
                import redis.asyncio as aioredis
                self._client = aioredis.from_url(redis_url, decode_responses=True)
                await self._client.ping()
                self._mode = "redis"
                logger.info("Redis: connected to %s", redis_url)
            except Exception as e:
                logger.warning("Redis: connection failed (%s), falling back to in-memory", e)
                self._mode = "memory"
        else:
            self._mode = "memory"
            logger.info("Redis: no URL configured, using in-memory")

    async def _upstash_command(self, method: str, *args) -> Optional[str]:
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._upstash_url,
                    headers={"Authorization": f"Bearer {self._upstash_token}"},
                    json=[method, *args],
                    timeout=5,
                )
                return resp.text
        except Exception as e:
            logger.warning("Upstash command failed: %s", e)
            return None

    async def incr(self, key: str, expire: int = 86400) -> int:
        if self._mode == "upstash":
            val = await self._upstash_command("INCR", key)
            if val is not None:
                count = int(val)
                if count == 1:
                    await self._upstash_command("EXPIRE", key, str(expire))
                return count
        elif self._mode == "redis" and self._client:
            try:
                count = await self._client.incr(key)
                if count == 1:
                    await self._client.expire(key, expire)
                return count
            except Exception:
                pass
        now = time.time()
        lst = self._in_memory.setdefault(key, [])
        lst.append(now)
        cutoff = now - expire
        self._in_memory[key] = [t for t in lst if t > cutoff]
        return len(self._in_memory[key])

    async def get(self, key: str) -> Optional[str]:
        if self._mode == "upstash":
            return await self._upstash_command("GET", key)
        if self._mode == "redis" and self._client:
            try:
                return await self._client.get(key)
            except Exception:
                pass
        return None

    async def set(self, key: str, value: str, expire: int = 86400):
        if self._mode == "upstash":
            await self._upstash_command("SET", key, value, "EX", str(expire))
        elif self._mode == "redis" and self._client:
            try:
                await self._client.set(key, value, ex=expire)
            except Exception:
                pass
        else:
            self._in_memory[key] = [time.time()]

    async def delete(self, key: str):
        if self._mode == "upstash":
            await self._upstash_command("DEL", key)
        elif self._mode == "redis" and self._client:
            try:
                await self._client.delete(key)
            except Exception:
                pass
        else:
            self._in_memory.pop(key, None)

    async def exists(self, key: str) -> bool:
        if self._mode == "upstash":
            val = await self._upstash_command("EXISTS", key)
            return val == "1" if val else False
        if self._mode == "redis" and self._client:
            try:
                return await self._client.exists(key) > 0
            except Exception:
                pass
        return key in self._in_memory


redis_service = RedisService()


async def init_redis():
    from app.config import get_settings
    s = get_settings()
    await redis_service.initialize(
        upstash_url=s.UPSTASH_REDIS_URL,
        upstash_token=s.UPSTASH_REDIS_TOKEN,
        redis_url=s.REDIS_URL,
    )
