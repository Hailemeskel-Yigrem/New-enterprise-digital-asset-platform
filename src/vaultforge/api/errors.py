"""Global exception handlers for VaultForge API errors."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from vaultforge.core.exceptions import VaultForgeError


def _status_for_code(code: str) -> int:
    return {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
        "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
    }.get(code, status.HTTP_400_BAD_REQUEST)


async def vaultforge_error_handler(_: Request, exc: VaultForgeError) -> JSONResponse:
    return JSONResponse(
        status_code=_status_for_code(exc.code),
        content={"code": exc.code, "message": exc.message},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(VaultForgeError, vaultforge_error_handler)
