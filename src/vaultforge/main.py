"""ASGI entrypoint for VaultForge."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vaultforge import __version__
from vaultforge.api.errors import register_exception_handlers
from vaultforge.api.health import router as health_router
from vaultforge.api.middleware import RequestIdMiddleware, TimingMiddleware
from vaultforge.api.middleware.rate_limit import RateLimitMiddleware
from vaultforge.api.monitoring import router as monitoring_router
from vaultforge.api.v1.router import api_v1_router
from vaultforge.api.ws.notifications import router as ws_router
from vaultforge.core.config import get_settings
from vaultforge.core.logging import configure_logging, get_logger


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.app_debug)
    log = get_logger("vaultforge.startup")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    register_exception_handlers(app)

    app.add_middleware(TimingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    app.include_router(health_router)
    app.include_router(monitoring_router)
    app.include_router(api_v1_router, prefix=settings.app_api_prefix)
    app.include_router(ws_router)

    @app.on_event("startup")
    async def on_startup() -> None:
        log.info("app_started", env=settings.app_env, version=__version__)

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "vaultforge.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug and not settings.is_production,
    )


if __name__ == "__main__":
    run()
