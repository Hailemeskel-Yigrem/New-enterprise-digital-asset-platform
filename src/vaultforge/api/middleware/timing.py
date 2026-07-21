"""Measure and expose HTTP request duration."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from vaultforge.core.logging import get_logger

RESPONSE_TIME_HEADER = "X-Response-Time-Ms"
SLOW_REQUEST_MS = 1000.0

log = get_logger("vaultforge.http")


class TimingMiddleware(BaseHTTPMiddleware):
    """Add X-Response-Time-Ms header and log slow requests.

    This is the innermost middleware in the stack, sitting directly above
    the router. Catching unhandled exceptions here (rather than letting
    them propagate through the outer ``BaseHTTPMiddleware`` layers) avoids
    a known Starlette pitfall where exceptions raised deep in the ASGI
    call chain can fail to reach ``ServerErrorMiddleware`` cleanly once
    several ``BaseHTTPMiddleware`` instances are stacked.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 - last line of defense before outer middleware
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            log.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(elapsed_ms, 2),
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "code": "internal_error",
                    "message": "An unexpected error occurred while processing the request.",
                },
            )
            response.headers[RESPONSE_TIME_HEADER] = f"{elapsed_ms:.2f}"
            return response
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
