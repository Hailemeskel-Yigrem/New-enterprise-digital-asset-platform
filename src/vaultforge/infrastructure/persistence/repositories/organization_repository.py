"""SQLAlchemy implementation of OrganizationRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.identity.entities import Organization
from vaultforge.domain.identity.repositories import OrganizationRepository
from vaultforge.infrastructure.persistence.models.membership import MembershipModel
from vaultforge.infrastructure.persistence.models.organization import OrganizationModel


def _to_entity(model: OrganizationModel) -> Organization:
    return Organization(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        name=model.name,
        slug=model.slug,
        is_active=model.is_active,
        plan_code=model.plan_code,
        max_storage_gb=model.max_storage_gb,
    )


class SqlAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self._session.execute(
            select(OrganizationModel).where(OrganizationModel.id == org_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self._session.execute(
            select(OrganizationModel).where(OrganizationModel.slug == slug)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def add(self, organization: Organization) -> Organization:
        model = OrganizationModel(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            is_active=organization.is_active,
            plan_code=organization.plan_code,
            max_storage_gb=organization.max_storage_gb,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def update(self, organization: Organization) -> Organization:
        result = await self._session.execute(
            select(OrganizationModel).where(OrganizationModel.id == organization.id)
        )
        model = result.scalar_one()
        model.name = organization.name
        model.slug = organization.slug
        model.is_active = organization.is_active
        model.plan_code = organization.plan_code
        model.max_storage_gb = organization.max_storage_gb
        model.updated_at = organization.updated_at
        await self._session.flush()
        return _to_entity(model)

    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Organization]:
        stmt = (
            select(OrganizationModel)
            .join(MembershipModel, MembershipModel.organization_id == OrganizationModel.id)
            .where(MembershipModel.user_id == user_id)
            .order_by(OrganizationModel.name)
        )
        result = await self._session.execute(stmt)
        return [_to_entity(model) for model in result.scalars().all()]
