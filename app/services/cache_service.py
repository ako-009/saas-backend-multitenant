import json
import redis.asyncio as aioredis
from typing import Optional, Any
from app.core.config import settings


def get_redis_client():
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True
    )


class CacheService:
    """
    Cache-aside implementation using Redis.
    
    KEY NAMING CONVENTION:
    tenant:{tenant_id}:users         → list of all users
    tenant:{tenant_id}:user:{id}     → single user
    tenant:{tenant_id}:user_roles    → role data for RBAC
    """

    @staticmethod
    def _make_key(tenant_id: str, key: str) -> str:
        return f"tenant:{tenant_id}:{key}"

    @staticmethod
    async def get(tenant_id: str, key: str) -> Optional[Any]:
        try:
            r = get_redis_client()
            cache_key = CacheService._make_key(tenant_id, key)
            value = await r.get(cache_key)
            await r.aclose()
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache GET error: {e}")
            return None

    @staticmethod
    async def set(tenant_id: str, key: str, value: Any, ttl: int = 300) -> bool:
        try:
            r = get_redis_client()
            cache_key = CacheService._make_key(tenant_id, key)
            await r.setex(cache_key, ttl, json.dumps(value))
            await r.aclose()
            return True
        except Exception as e:
            print(f"Cache SET error: {e}")
            return False

    @staticmethod
    async def delete(tenant_id: str, key: str) -> bool:
        try:
            r = get_redis_client()
            cache_key = CacheService._make_key(tenant_id, key)
            await r.delete(cache_key)
            await r.aclose()
            return True
        except Exception as e:
            print(f"Cache DELETE error: {e}")
            return False

    @staticmethod
    async def delete_pattern(tenant_id: str, pattern: str) -> bool:
        try:
            r = get_redis_client()
            cache_key_pattern = CacheService._make_key(tenant_id, pattern)
            keys = await r.keys(cache_key_pattern)
            if keys:
                await r.delete(*keys)
            await r.aclose()
            return True
        except Exception as e:
            print(f"Cache DELETE PATTERN error: {e}")
            return False


cache = CacheService()