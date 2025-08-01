"""Integration tests for authentication API flow."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from vaultforge.api.deps import get_auth_service, get_current_user, get_db
from vaultforge.application.identity.auth_service import AuthService
from vaultforge.application.identity.schemas import TokenResponse, UserResponse
from vaultforge.core.exceptions import AuthenticationError, ConflictError
from vaultforge.domain.identity.entities import User
from vaultforge.infrastructure.security import hash_password


def _user_response(**overrides: object) -> UserResponse:
    now = datetime.now(timezone.utc)
    data = {
        "id": uuid.uuid4(),
        "email": "flow@example.com",
        "full_name": "Flow User",
        "is_active": True,
        "is_email_verified": True,
        "last_login_at": None,
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return UserResponse(**data)


@pytest.fixture
def auth_client(client: TestClient):
    mock_service = AsyncMock(spec=AuthService)
    stored_user = User(
        id=uuid.uuid4(),
        email="flow@example.com",
        full_name="Flow User",
        password_hash=hash_password("FlowPass123!"),
        is_active=True,
        is_email_verified=True,
    )

    async def register(payload: object) -> UserResponse:
        return UserResponse.model_validate(stored_user)

    async def login(payload: object) -> TokenResponse:
        from vaultforge.infrastructure.security import create_access_token, create_refresh_token

        return TokenResponse(
            access_token=create_access_token(stored_user.id),
            refresh_token=create_refresh_token(stored_user.id),
        )

    mock_service.register = AsyncMock(side_effect=register)
    mock_service.login = AsyncMock(side_effect=login)
    mock_service.refresh = AsyncMock(
        side_effect=lambda payload: login(payload),
    )
    mock_service.get_user = AsyncMock(
        return_value=UserResponse.model_validate(stored_user),
    )

    async def override_db():
        yield AsyncMock()

    app = client.app
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: UserResponse.model_validate(stored_user)

    yield client, mock_service, stored_user
    app.dependency_overrides.clear()


def test_register_returns_201(auth_client: tuple[TestClient, AsyncMock, User]) -> None:
    client, mock_service, _ = auth_client
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "new@example.com",
            "password": "SecurePass123!",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "flow@example.com"
    mock_service.register.assert_awaited()


def test_login_returns_bearer_tokens(auth_client: tuple[TestClient, AsyncMock, User]) -> None:
    client, _, _ = auth_client
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "FlowPass123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


def test_me_requires_auth_when_override_removed(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


def test_me_returns_user_with_override(auth_client: tuple[TestClient, AsyncMock, User]) -> None:
    client, _, user = auth_client
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_login_maps_service_errors(client: TestClient) -> None:
    mock_service = AsyncMock(spec=AuthService)
    mock_service.login = AsyncMock(side_effect=AuthenticationError("Invalid email or password"))

    async def override_db():
        yield AsyncMock()

    app = client.app
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: mock_service

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "bad@example.com", "password": "wrong"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "unauthorized"


def test_register_conflict_returns_409(client: TestClient) -> None:
    mock_service = AsyncMock(spec=AuthService)
    mock_service.register = AsyncMock(side_effect=ConflictError("Email is already registered"))

    async def override_db():
        yield AsyncMock()

    app = client.app
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_auth_service] = lambda: mock_service

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "dup@example.com",
            "password": "SecurePass123!",
            "full_name": "Dup",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "conflict"
