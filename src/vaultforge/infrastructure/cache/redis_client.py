"""Async Redis client wrapper with circuit-breaker protection."""

from __future__ import annotations

from functools import lru_cache

import redis.asyncio as aioredis
from redis.asyncio import Redis

from vaultforge.core.config import get_settings
from vaultforge.infrastructure.resilience import CircuitBreaker


class RedisClient:
    def __init__(self, redis: Redis, *, circuit: CircuitBreaker | None = None) -> None:
        self._redis = redis
        self._circuit = circuit or CircuitBreaker("redis", failure_threshold=5)

    async def ping(self) -> bool:
        return bool(await self._circuit.call(self._redis.ping))

    async def get(self, key: str) -> str | None:
        async def _get() -> object:
            return await self._redis.get(key)

        value = await self._circuit.call(_get)
        if value is None:
            return None
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def set(self, key: str, value: str, *, ex: int | None = None) -> None:
        async def _set() -> object:
            return await self._redis.set(key, value, ex=ex)

        await self._circuit.call(_set)

    async def delete(self, key: str) -> None:
        async def _delete() -> object:
            return await self._redis.delete(key)

        await self._circuit.call(_delete)

    async def close(self) -> None:
        await self._redis.aclose()

    @property
    def circuit_state(self) -> str:
        return self._circuit.state.value


@lru_cache
def get_redis_client() -> RedisClient:
    settings = get_settings()
    redis = aioredis.from_url(  # type: ignore[no-untyped-call]
        settings.redis_url, decode_responses=False
    )
    return RedisClient(redis)
