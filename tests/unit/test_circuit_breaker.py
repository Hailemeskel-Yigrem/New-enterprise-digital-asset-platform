"""Unit tests for circuit breaker resilience helper."""

from __future__ import annotations

import pytest

from vaultforge.infrastructure.resilience import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)


@pytest.mark.asyncio
async def test_circuit_opens_after_threshold_failures() -> None:
    breaker = CircuitBreaker("test", failure_threshold=2, max_retries=0)

    async def boom() -> None:
        raise RuntimeError("downstream down")

    with pytest.raises(RuntimeError):
        await breaker.call(boom)
    with pytest.raises(RuntimeError):
        await breaker.call(boom)

    assert breaker.state == CircuitState.OPEN
    with pytest.raises(CircuitBreakerOpenError):
        await breaker.call(boom)


@pytest.mark.asyncio
async def test_circuit_recovers_to_half_open_after_timeout() -> None:
    breaker = CircuitBreaker(
        "recover",
        failure_threshold=1,
        recovery_timeout_seconds=0.0,
        max_retries=0,
    )

    async def boom() -> None:
        raise RuntimeError("down")

    with pytest.raises(RuntimeError):
        await breaker.call(boom)
    assert breaker.state == CircuitState.HALF_OPEN

    async def ok() -> str:
        return "up"

    assert await breaker.call(ok) == "up"
    assert breaker.state == CircuitState.CLOSED
