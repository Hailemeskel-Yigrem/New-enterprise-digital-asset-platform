"""SQLAlchemy implementation of MembershipRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.identity.entities import Membership
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole
from vaultforge.domain.identity.repositories import MembershipRepository
from vaultforge.infrastructure.persistence.models.membership import MembershipModel


def _to_entity(model: MembershipModel) -> Membership:
    return Membership(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        organization_id=model.organization_id,
        user_id=model.user_id,
        role=OrgRole(model.role),
        status=MembershipStatus(model.status),
    )


class SqlAlchemyMembershipRepository(MembershipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None:
        result = await self._session.execute(
            select(MembershipModel).where(
                MembershipModel.organization_id == organization_id,
                MembershipModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def add(self, membership: Membership) -> Membership:
        model = MembershipModel(
            id=membership.id,
            organization_id=membership.organization_id,
            user_id=membership.user_id,
            role=membership.role.value,
            status=membership.status.value,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update(self, membership: Membership) -> Membership:
        result = await self._session.execute(
            select(MembershipModel).where(MembershipModel.id == membership.id)
        )
        model = result.scalar_one()
        model.role = membership.role.value
        model.status = membership.status.value
        model.updated_at = membership.updated_at
        await self._session.flush()
        return _to_entity(model)

    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Membership]:
        result = await self._session.execute(
            select(MembershipModel)
            .where(MembershipModel.organization_id == organization_id)
            .order_by(MembershipModel.created_at)
        )
        return [_to_entity(model) for model in result.scalars().all()]
