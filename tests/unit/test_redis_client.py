"""Additional coverage for redis client circuit wiring."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from vaultforge.infrastructure.cache.redis_client import RedisClient
from vaultforge.infrastructure.resilience import CircuitBreaker, CircuitState


@pytest.mark.asyncio
async def test_redis_client_get_set_delete_via_circuit() -> None:
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=b"value")
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    client = RedisClient(redis, circuit=CircuitBreaker("redis-test", max_retries=0))

    assert await client.ping() is True
    assert await client.get("k") == "value"
    await client.set("k", "v", ex=10)
    await client.delete("k")
    assert client.circuit_state == CircuitState.CLOSED.value


@pytest.mark.asyncio
async def test_redis_client_get_none() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    client = RedisClient(redis, circuit=CircuitBreaker("redis-none", max_retries=0))
    assert await client.get("missing") is None
