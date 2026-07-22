"""Unit tests for rate limiting middleware."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from vaultforge.api.middleware.rate_limit import (
    InMemoryRateLimitStore,
    RateLimiter,
    RateLimitRule,
    build_default_rules,
)


def _make_request(path: str = "/api/v1/auth/login", method: str = "POST") -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
        "client": ("127.0.0.1", 12345),
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_rate_limit_allows_under_threshold() -> None:
    store = InMemoryRateLimitStore()
    rule = RateLimitRule(name="test", requests=5, window_seconds=60)
    limiter = RateLimiter(rules=[rule], store=store)
    request = _make_request("/anything")
    allowed, matched, count, _ = await limiter.check(request)
    assert allowed
    assert matched == rule
    assert count == 1


@pytest.mark.asyncio
async def test_rate_limit_blocks_over_threshold() -> None:
    store = InMemoryRateLimitStore()
    rule = RateLimitRule(name="test", requests=2, window_seconds=60, path_prefix="/limited")
    limiter = RateLimiter(rules=[rule], store=store)
    request = _make_request("/limited/resource")
    await limiter.check(request)
    await limiter.check(request)
    allowed, matched, count, retry = await limiter.check(request)
    assert not allowed
    assert matched == rule
    assert count == 3
    assert retry >= 0


@pytest.mark.asyncio
async def test_rule_path_prefix_matching() -> None:
    store = InMemoryRateLimitStore()
    rule = RateLimitRule(
        name="auth",
        requests=1,
        window_seconds=60,
        path_prefix="/api/v1/auth",
        methods=frozenset({"POST"}),
    )
    limiter = RateLimiter(rules=[rule], store=store)
    allowed, _, _, _ = await limiter.check(_make_request("/api/v1/auth/login", "POST"))
    assert allowed
    allowed, _, _, _ = await limiter.check(_make_request("/api/v1/documents", "GET"))
    assert allowed


def test_build_default_rules() -> None:
    rules = build_default_rules()
    assert any(r.name == "global" for r in rules)
    assert any(r.name == "oauth" for r in rules)


@pytest.mark.asyncio
async def test_store_reset() -> None:
    store = InMemoryRateLimitStore()
    await store.increment("key", 60)
    await store.reset("key")
    count, _ = await store.increment("key", 60)
    assert count == 1
