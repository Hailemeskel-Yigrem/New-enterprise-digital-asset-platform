"""Shared pytest fixtures."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from vaultforge.application.identity.schemas import UserResponse
from vaultforge.core.context import bind_context, clear_context
from vaultforge.core.pagination import PageParams
from vaultforge.infrastructure.security import create_access_token


@pytest.fixture(scope="session", autouse=True)
def _test_env() -> None:
    os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32chars-minimum!!")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32chars-min!!")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("APP_DEBUG", "true")
    from vaultforge.core.config import clear_settings_cache

    clear_settings_cache()
    os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(autouse=True)
def _reset_request_context() -> Iterator[None]:
    clear_context()
    yield
    clear_context()


@pytest.fixture
def sample_user_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-4111-8111-111111111111")


@pytest.fixture
def sample_org_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-4222-8222-222222222222")


@pytest.fixture
def sample_team_id() -> uuid.UUID:
    return uuid.UUID("33333333-3333-4333-8333-333333333333")


@pytest.fixture
def sample_request_id() -> str:
    return "test-request-id-00000001"


@pytest.fixture
def sample_user_response(sample_user_id: uuid.UUID) -> UserResponse:
    now = datetime.now(UTC)
    return UserResponse(
        id=sample_user_id,
        email="tester@example.com",
        full_name="Test User",
        is_active=True,
        is_email_verified=True,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def auth_headers(sample_user_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(sample_user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def org_auth_headers(auth_headers: dict[str, str], sample_org_id: uuid.UUID) -> dict[str, str]:
    return {
        **auth_headers,
        "X-Organization-Id": str(sample_org_id),
    }


@pytest.fixture
def page_params() -> PageParams:
    return PageParams(page=1, page_size=25)


@pytest.fixture
def large_page_params() -> PageParams:
    return PageParams(page=2, page_size=100)


@pytest.fixture
def mock_db_session() -> AsyncMock:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    return session


@pytest.fixture
def mock_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_user_repository(sample_user_response: UserResponse) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=sample_user_response)
    repo.update = AsyncMock(return_value=sample_user_response)
    return repo


@pytest.fixture
def bound_request_context(
    sample_org_id: uuid.UUID,
    sample_user_id: uuid.UUID,
    sample_request_id: str,
) -> Iterator[None]:
    with bind_context(
        org_id=sample_org_id,
        user_id=sample_user_id,
        request_id=sample_request_id,
    ):
        yield


@pytest.fixture
def sample_pagination_items() -> list[dict[str, Any]]:
    return [{"id": i, "name": f"item-{i}"} for i in range(1, 51)]


@pytest.fixture
def client(_test_env: None) -> Iterator[TestClient]:
    from vaultforge.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
