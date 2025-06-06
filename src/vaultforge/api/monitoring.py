"""Prometheus-style metrics and dependency health probes."""

from __future__ import annotations

from collections import defaultdict
from threading import Lock

from fastapi import APIRouter, Response
from pydantic import BaseModel
from sqlalchemy import text

from vaultforge.infrastructure.cache import get_redis_client
from vaultforge.infrastructure.persistence.session import engine

router = APIRouter(tags=["monitoring"])

_lock = Lock()
_counters: dict[str, int] = defaultdict(int)


class DependencyStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None


class DependencyHealthResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]


def increment_counter(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] += amount


def snapshot_counters() -> dict[str, int]:
    with _lock:
        return dict(_counters)


@router.get("/metrics")
async def metrics() -> Response:
    lines: list[str] = []
    for name, value in sorted(snapshot_counters().items()):
        metric = name.replace("-", "_")
        lines.append(f"# TYPE {metric} counter")
        lines.append(f"{metric} {value}")
    if not lines:
        lines.append("# TYPE vaultforge_up counter")
        lines.append("vaultforge_up 1")
    body = "\n".join(lines) + "\n"
    return Response(content=body, media_type="text/plain; version=0.0.4")


@router.get("/health/deps", response_model=DependencyHealthResponse)
async def health_dependencies() -> DependencyHealthResponse:
    dependencies: list[DependencyStatus] = []

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        dependencies.append(DependencyStatus(name="database", status="ok"))
    except Exception as exc:
        dependencies.append(
            DependencyStatus(name="database", status="error", detail=str(exc))
        )

    try:
        redis = get_redis_client()
        if await redis.ping():
            dependencies.append(DependencyStatus(name="redis", status="ok"))
        else:
            dependencies.append(DependencyStatus(name="redis", status="error", detail="ping failed"))
    except Exception as exc:
        dependencies.append(DependencyStatus(name="redis", status="error", detail=str(exc)))

    overall = "ok" if all(item.status == "ok" for item in dependencies) else "degraded"
    return DependencyHealthResponse(status=overall, dependencies=dependencies)
