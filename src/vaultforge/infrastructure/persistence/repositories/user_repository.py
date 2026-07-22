"""SQLAlchemy implementation of UserRepository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.identity.entities import User
from vaultforge.domain.identity.repositories import UserRepository
from vaultforge.infrastructure.persistence.models.user import UserModel


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        email=model.email,
        full_name=model.full_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        is_email_verified=model.is_email_verified,
        last_login_at=model.last_login_at,
    )


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user_id))
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email.lower())
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def add(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email.lower(),
            full_name=user.full_name,
            password_hash=user.password_hash,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update(self, user: User) -> User:
        result = await self._session.execute(select(UserModel).where(UserModel.id == user.id))
        model = result.scalar_one()
        model.email = user.email.lower()
        model.full_name = user.full_name
        model.password_hash = user.password_hash
        model.is_active = user.is_active
        model.is_email_verified = user.is_email_verified
        model.last_login_at = user.last_login_at
        model.updated_at = user.updated_at
        await self._session.flush()
        return _to_entity(model)
