from typing import Optional
from app.services.redis_service import redis_service


class RateLimiter:
    async def _check(self, org_id: str, channel: str, max_per_day: int = 20) -> tuple[bool, int]:
        key = f"ratelimit:{org_id}:{channel}"
        count = await redis_service.incr(key, expire=86400)
        return (count <= max_per_day), max(0, max_per_day - count)

    async def check_email(self, org_id: str, max_per_day: int = 20) -> tuple[bool, int]:
        return await self._check(org_id, "email", max_per_day)

    async def check_call(self, org_id: str, max_per_day: int = 10) -> tuple[bool, int]:
        return await self._check(org_id, "call", max_per_day)

    async def check_linkedin(self, org_id: str, max_per_day: int = 15) -> tuple[bool, int]:
        return await self._check(org_id, "linkedin", max_per_day)

    async def get_usage(self, org_id: str) -> dict:
        channels = ["email", "call", "linkedin"]
        result = {}
        for ch in channels:
            val = await redis_service.get(f"ratelimit:{org_id}:{ch}")
            result[f"{ch}s_today"] = int(val) if val else 0
        return result

    async def reset_org(self, org_id: str):
        for ch in ("email", "call", "linkedin"):
            await redis_service.delete(f"ratelimit:{org_id}:{ch}")


rate_limiter = RateLimiter()
