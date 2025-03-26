"""Authentication application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.identity.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from vaultforge.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from vaultforge.domain.common import utc_now
from vaultforge.domain.identity.entities import User
from vaultforge.domain.identity.repositories import UserRepository
from vaultforge.infrastructure.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)


@dataclass(slots=True)
class AuthService:
    users: UserRepository

    async def register(self, payload: RegisterRequest) -> UserResponse:
        existing = await self.users.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError("Email is already registered")

        user = User(
            email=payload.email.lower(),
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            is_active=True,
            is_email_verified=False,
        )
        created = await self.users.add(user)
        return UserResponse.model_validate(created)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.users.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is inactive")

        user.last_login_at = utc_now()
        user.touch()
        await self.users.update(user)

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        user_id = get_user_id_from_token(
            payload.refresh_token,
            expected_type=TOKEN_TYPE_REFRESH,
        )
        user = await self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account unavailable")

        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
        )

    async def get_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return UserResponse.model_validate(user)
