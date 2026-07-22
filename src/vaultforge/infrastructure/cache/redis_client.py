"""Async Redis client wrapper."""

from __future__ import annotations

from functools import lru_cache

import redis.asyncio as aioredis
from redis.asyncio import Redis

from vaultforge.core.config import get_settings


class RedisClient:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(key)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        await self._redis.set(key, value, ex=ex)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def close(self) -> None:
        await self._redis.aclose()


@lru_cache
def get_redis_client() -> RedisClient:
    settings = get_settings()
    redis = aioredis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, decode_responses=False
    )
    return RedisClient(redis)
