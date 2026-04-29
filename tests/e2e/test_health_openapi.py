"""End-to-end smoke tests for health and OpenAPI surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vaultforge import __version__


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


def test_ready_endpoint_accessible(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] in {"ready", "degraded"}


def test_openapi_schema_exposes_core_tags(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"]
    paths = schema.get("paths", {})
    assert any(path.startswith("/api/v1/auth") for path in paths)
    assert any(path.startswith("/api/v1/organizations") for path in paths)
    tag_names = {tag["name"] for tag in schema.get("tags", [])}
    expected = {"auth", "organizations", "documents", "health"}
    assert expected.issubset(tag_names)


def test_docs_ui_available(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()


def test_request_id_header_present(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_response_time_header_present(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Response-Time-Ms" in response.headers


def test_openapi_lists_auth_paths(client) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})
    assert "/health" in paths or any("auth" in path for path in paths)
