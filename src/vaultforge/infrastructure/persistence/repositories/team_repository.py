"""SQLAlchemy implementation of TeamRepository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vaultforge.domain.identity.entities import Team
from vaultforge.domain.identity.repositories import TeamRepository
from vaultforge.infrastructure.persistence.models.team import TeamMemberModel, TeamModel


def _to_entity(model: TeamModel) -> Team:
    return Team(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        member_ids=[member.user_id for member in model.members],
    )


class SqlAlchemyTeamRepository(TeamRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, team_id: uuid.UUID) -> Team | None:
        result = await self._session.execute(
            select(TeamModel)
            .options(selectinload(TeamModel.members))
            .where(TeamModel.id == team_id)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def add(self, team: Team) -> Team:
        model = TeamModel(
            id=team.id,
            organization_id=team.organization_id,
            name=team.name,
            description=team.description,
            created_at=team.created_at,
            updated_at=team.updated_at,
        )
        self._session.add(model)
        await self._session.flush()

        for user_id in team.member_ids:
            self._session.add(TeamMemberModel(team_id=model.id, user_id=user_id))
        await self._session.flush()

        result = await self._session.execute(
            select(TeamModel)
            .options(selectinload(TeamModel.members))
            .where(TeamModel.id == model.id)
        )
        refreshed = result.scalar_one()
        return _to_entity(refreshed)

    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Team]:
        result = await self._session.execute(
            select(TeamModel)
            .options(selectinload(TeamModel.members))
            .where(TeamModel.organization_id == organization_id)
            .order_by(TeamModel.name)
        )
        return [_to_entity(model) for model in result.scalars().all()]

    async def add_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> Team:
        self._session.add(TeamMemberModel(team_id=team_id, user_id=user_id))
        await self._session.flush()
        team = await self.get_by_id(team_id)
        if team is None:
            msg = "Team not found after adding member"
            raise RuntimeError(msg)
        return team
