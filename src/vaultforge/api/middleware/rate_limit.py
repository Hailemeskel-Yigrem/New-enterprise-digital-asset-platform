"""Redis-backed rate limiting middleware for FastAPI."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from vaultforge.core.config import Settings, get_settings
from vaultforge.core.logging import get_logger

log = get_logger(__name__)


class RateLimitScope(StrEnum):
    IP = "ip"
    USER = "user"
    CLIENT = "client"
    GLOBAL = "global"


@dataclass(slots=True)
class RateLimitRule:
    name: str
    requests: int
    window_seconds: int
    scope: RateLimitScope = RateLimitScope.IP
    path_prefix: str | None = None
    methods: frozenset[str] | None = None

    def matches(self, request: Request) -> bool:
        if self.path_prefix and not request.url.path.startswith(self.path_prefix):
            return False
        return not (self.methods and request.method.upper() not in self.methods)


@dataclass(slots=True)
class RateLimitState:
    count: int = 0
    window_start: float = field(default_factory=time.time)


class InMemoryRateLimitStore:
    """Process-local rate limit counter store (for tests and fallback)."""

    def __init__(self) -> None:
        self._buckets: dict[str, RateLimitState] = {}

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        now = time.time()
        state = self._buckets.get(key)
        if state is None or now - state.window_start >= window_seconds:
            state = RateLimitState(count=0, window_start=now)
            self._buckets[key] = state
        state.count += 1
        remaining = max(0, window_seconds - int(now - state.window_start))
        return state.count, remaining

    async def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


class RedisRateLimitStore:
    """Redis-backed sliding window counter."""

    def __init__(self, redis_client: Any, *, key_prefix: str = "rl:") -> None:
        self._redis = redis_client
        self._prefix = key_prefix

    async def increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        full_key = f"{self._prefix}{key}"
        pipe = self._redis._redis.pipeline()
        pipe.incr(full_key)
        pipe.ttl(full_key)
        count, ttl = await pipe.execute()
        if ttl == -1:
            await self._redis._redis.expire(full_key, window_seconds)
            ttl = window_seconds
        return int(count), int(ttl)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _scope_key(request: Request, rule: RateLimitRule) -> str:
    if rule.scope == RateLimitScope.IP:
        return f"ip:{_client_ip(request)}"
    if rule.scope == RateLimitScope.USER:
        auth = request.headers.get("Authorization", "")
        if auth:
            digest = hashlib.sha256(auth.encode()).hexdigest()[:16]
            return f"user:{digest}"
        return f"ip:{_client_ip(request)}"
    if rule.scope == RateLimitScope.CLIENT:
        client_id = request.headers.get("X-Client-Id", "anonymous")
        return f"client:{client_id}"
    return "global"


def build_default_rules(settings: Settings | None = None) -> list[RateLimitRule]:
    cfg = settings or get_settings()
    return [
        RateLimitRule(
            name="global",
            requests=cfg.rate_limit_global_requests,
            window_seconds=cfg.rate_limit_global_window,
            scope=RateLimitScope.IP,
        ),
        RateLimitRule(
            name="auth",
            requests=cfg.rate_limit_auth_requests,
            window_seconds=cfg.rate_limit_auth_window,
            scope=RateLimitScope.IP,
            path_prefix="/api/v1/auth",
            methods=frozenset({"POST"}),
        ),
        RateLimitRule(
            name="oauth",
            requests=cfg.rate_limit_oauth_requests,
            window_seconds=cfg.rate_limit_oauth_window,
            scope=RateLimitScope.IP,
            path_prefix="/api/v1/oauth",
            methods=frozenset({"POST"}),
        ),
        RateLimitRule(
            name="export",
            requests=cfg.rate_limit_export_requests,
            window_seconds=cfg.rate_limit_export_window,
            scope=RateLimitScope.USER,
            path_prefix="/api/v1/organizations",
            methods=frozenset({"POST"}),
        ),
    ]


@dataclass(slots=True)
class RateLimiter:
    rules: list[RateLimitRule]
    store: InMemoryRateLimitStore | RedisRateLimitStore

    async def check(self, request: Request) -> tuple[bool, RateLimitRule | None, int, int]:
        """Return (allowed, matched_rule, current_count, retry_after)."""
        for rule in self.rules:
            if not rule.matches(request):
                continue
            scope = _scope_key(request, rule)
            bucket_key = f"{rule.name}:{scope}:{request.url.path}"
            count, retry_after = await self.store.increment(bucket_key, rule.window_seconds)
            if count > rule.requests:
                log.warning(
                    "rate_limit_exceeded",
                    rule=rule.name,
                    path=request.url.path,
                    count=count,
                )
                return False, rule, count, retry_after
            return True, rule, count, retry_after
        return True, None, 0, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """ASGI middleware enforcing configurable rate limits."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        limiter: RateLimiter | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)
        settings = get_settings()
        self.enabled = enabled and settings.rate_limit_enabled
        if limiter is not None:
            self.limiter = limiter
        else:
            store: InMemoryRateLimitStore | RedisRateLimitStore
            try:
                from vaultforge.infrastructure.cache.redis_client import get_redis_client

                store = RedisRateLimitStore(get_redis_client())
            except Exception:
                store = InMemoryRateLimitStore()
            self.limiter = RateLimiter(rules=build_default_rules(settings), store=store)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not self.enabled or request.url.path in {"/health", "/ready", "/metrics"}:
            return await call_next(request)

        allowed, rule, count, retry_after = await self.limiter.check(request)
        if not allowed and rule is not None:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "code": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded for {rule.name}",
                    "retry_after": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        if rule is not None:
            remaining = max(0, rule.requests - count)
            response.headers["X-RateLimit-Limit"] = str(rule.requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


def create_rate_limit_middleware(
    app: ASGIApp,
    *,
    settings: Settings | None = None,
) -> RateLimitMiddleware:
    cfg = settings or get_settings()
    store = InMemoryRateLimitStore()
    limiter = RateLimiter(rules=build_default_rules(cfg), store=store)
    return RateLimitMiddleware(app, limiter=limiter, enabled=cfg.rate_limit_enabled)
