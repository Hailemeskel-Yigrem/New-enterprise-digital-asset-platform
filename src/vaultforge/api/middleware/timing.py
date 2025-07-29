"""Measure and expose HTTP request duration."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from vaultforge.core.logging import get_logger

RESPONSE_TIME_HEADER = "X-Response-Time-Ms"
SLOW_REQUEST_MS = 1000.0

log = get_logger("vaultforge.http")


class TimingMiddleware(BaseHTTPMiddleware):
    """Add X-Response-Time-Ms header and log slow requests."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        response.headers[RESPONSE_TIME_HEADER] = f"{elapsed_ms:.2f}"
        if elapsed_ms >= SLOW_REQUEST_MS:
            request_id = getattr(request.state, "request_id", "-")
            log.warning(
                "slow_request",
                method=request.method,
                path=request.url.path,
                duration_ms=round(elapsed_ms, 2),
                request_id=request_id,
            )
        return response
