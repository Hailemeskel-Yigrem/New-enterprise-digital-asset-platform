"""Integration tests for readiness and dependency health."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vaultforge.api.health import router as health_router
from vaultforge.api.monitoring import router as monitoring_router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(monitoring_router)
    return app


def test_ready_without_deps_returns_ready() -> None:
    client = TestClient(_app())
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_with_deps_includes_dependency_block() -> None:
    client = TestClient(_app())
    response = client.get("/ready", params={"check_deps": "true"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ready", "degraded"}
    assert "dependencies" in payload


def test_health_deps_endpoint_returns_dependency_list() -> None:
    client = TestClient(_app())
    response = client.get("/health/deps")
    assert response.status_code == 200
    payload = response.json()
    assert "dependencies" in payload
    names = {item["name"] for item in payload["dependencies"]}
    assert {"database", "redis"}.issubset(names)
