"""Liveness and readiness probes."""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import text

from vaultforge import __version__
from vaultforge.infrastructure.cache import get_redis_client
from vaultforge.infrastructure.persistence.session import get_engine

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str


class DependencyStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None


class ReadinessResponse(HealthResponse):
    dependencies: list[DependencyStatus] | None = None


async def _check_dependencies() -> list[DependencyStatus]:
    dependencies: list[DependencyStatus] = []

    try:
        async with get_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        dependencies.append(DependencyStatus(name="database", status="ok"))
    except Exception as exc:
        dependencies.append(DependencyStatus(name="database", status="error", detail=str(exc)))

    try:
        redis = get_redis_client()
        if await redis.ping():
            dependencies.append(DependencyStatus(name="redis", status="ok"))
        else:
            dependencies.append(
                DependencyStatus(name="redis", status="error", detail="ping failed")
            )
    except Exception as exc:
        dependencies.append(DependencyStatus(name="redis", status="error", detail=str(exc)))

    return dependencies


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@router.get("/ready", response_model=ReadinessResponse)
async def ready(
    check_deps: bool = Query(default=False, description="When true, probe database and redis"),
) -> ReadinessResponse:
    if not check_deps:
        return ReadinessResponse(status="ready", version=__version__)

    dependencies = await _check_dependencies()
    overall = "ready" if all(item.status == "ok" for item in dependencies) else "degraded"
    return ReadinessResponse(
        status=overall,
        version=__version__,
        dependencies=dependencies,
    )
