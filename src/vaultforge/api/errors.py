"""Global exception handlers for VaultForge API errors."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from vaultforge.core.error_tracking import capture_exception
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.core.logging import get_logger

log = get_logger("vaultforge.api.errors")


def _status_for_code(code: str) -> int:
    return {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
        "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(code, status.HTTP_400_BAD_REQUEST)


async def vaultforge_error_handler(_: Request, exc: VaultForgeError) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for_code(exc.code),
        content={"code": exc.code, "message": exc.message},
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
    )
    capture_exception(exc, path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "internal_error",
            "message": "An unexpected error occurred while processing the request.",
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    # Starlette's typing models exception handlers as taking the base
    # `Exception` type; the concrete handlers below are only ever invoked
    # with instances of the exception class they were registered for.
    app.add_exception_handler(
        VaultForgeError,
        vaultforge_error_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, unhandled_error_handler)
