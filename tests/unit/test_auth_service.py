"""Unit tests for AuthService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.identity.auth_service import AuthService
from vaultforge.application.identity.schemas import LoginRequest, RefreshRequest, RegisterRequest
from vaultforge.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from vaultforge.domain.identity.entities import User
from vaultforge.infrastructure.security import create_refresh_token, hash_password, verify_password


def _user(**overrides: object) -> User:
    now = datetime.now(UTC)
    base = User(
        id=uuid.uuid4(),
        email="alice@example.com",
        full_name="Alice Example",
        password_hash=hash_password("SecurePass123!"),
        is_active=True,
        is_email_verified=False,
        created_at=now,
        updated_at=now,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


@pytest.mark.asyncio
async def test_register_creates_user_when_email_available() -> None:
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    repo.add = AsyncMock(side_effect=lambda user: user)
    service = AuthService(users=repo)

    response = await service.register(
        RegisterRequest(email="new@example.com", password="SecurePass123!", full_name="New User")
    )

    assert response.email == "new@example.com"
    assert response.full_name == "New User"
    repo.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_rejects_duplicate_email() -> None:
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=_user())
    service = AuthService(users=repo)

    with pytest.raises(ConflictError, match="already registered"):
        await service.register(
            RegisterRequest(email="alice@example.com", password="SecurePass123!", full_name="Alice")
        )


@pytest.mark.asyncio
async def test_login_returns_tokens_for_valid_credentials() -> None:
    user = _user()
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    repo.update = AsyncMock(return_value=user)
    service = AuthService(users=repo)

    tokens = await service.login(LoginRequest(email="alice@example.com", password="SecurePass123!"))

    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"
    repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_login_rejects_invalid_password() -> None:
    user = _user()
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    service = AuthService(users=repo)

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.login(LoginRequest(email="alice@example.com", password="wrong-password"))


@pytest.mark.asyncio
async def test_login_rejects_inactive_user() -> None:
    user = _user(is_active=False)
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=user)
    service = AuthService(users=repo)

    with pytest.raises(AuthenticationError, match="inactive"):
        await service.login(LoginRequest(email="alice@example.com", password="SecurePass123!"))


@pytest.mark.asyncio
async def test_refresh_issues_new_tokens() -> None:
    user = _user()
    refresh = create_refresh_token(user.id)
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=user)
    service = AuthService(users=repo)

    tokens = await service.refresh(RefreshRequest(refresh_token=refresh))

    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_get_user_raises_when_missing() -> None:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    service = AuthService(users=repo)

    with pytest.raises(NotFoundError):
        await service.get_user(uuid.uuid4())


@pytest.mark.asyncio
async def test_password_hash_roundtrip() -> None:
    hashed = hash_password("test-password-99")
    assert verify_password("test-password-99", hashed)
    assert not verify_password("other", hashed)
