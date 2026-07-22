"""Team management application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.identity.schemas import (
    TeamCreate,
    TeamMemberAddRequest,
    TeamResponse,
)
from vaultforge.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from vaultforge.domain.identity.entities import Team
from vaultforge.domain.identity.enums import MembershipStatus, Permission
from vaultforge.domain.identity.repositories import (
    MembershipRepository,
    TeamRepository,
)


@dataclass(slots=True)
class TeamService:
    teams: TeamRepository
    memberships: MembershipRepository

    async def create_team(
        self,
        org_id: uuid.UUID,
        payload: TeamCreate,
        actor_id: uuid.UUID,
    ) -> TeamResponse:
        await self._require_permission(org_id, actor_id, Permission.TEAM_MANAGE)
        await self._validate_member_ids(org_id, payload.member_ids)

        team = Team(
            organization_id=org_id,
            name=payload.name,
            description=payload.description,
            member_ids=list(payload.member_ids),
        )
        created = await self.teams.add(team)
        return TeamResponse.model_validate(created)

    async def list_teams(self, org_id: uuid.UUID, actor_id: uuid.UUID) -> list[TeamResponse]:
        await self._require_active_membership(org_id, actor_id)
        teams = await self.teams.list_for_org(org_id)
        return [TeamResponse.model_validate(team) for team in teams]

    async def get_team(
        self,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> TeamResponse:
        await self._require_active_membership(org_id, actor_id)
        team = await self.teams.get_by_id(team_id)
        if team is None or team.organization_id != org_id:
            raise NotFoundError("Team not found")
        return TeamResponse.model_validate(team)

    async def add_member(
        self,
        org_id: uuid.UUID,
        team_id: uuid.UUID,
        payload: TeamMemberAddRequest,
        actor_id: uuid.UUID,
    ) -> TeamResponse:
        await self._require_permission(org_id, actor_id, Permission.TEAM_MANAGE)

        team = await self.teams.get_by_id(team_id)
        if team is None or team.organization_id != org_id:
            raise NotFoundError("Team not found")

        if payload.user_id in team.member_ids:
            raise ConflictError("User is already a team member")

        await self._validate_member_ids(org_id, [payload.user_id])
        updated = await self.teams.add_member(team_id, payload.user_id)
        return TeamResponse.model_validate(updated)

    async def _require_active_membership(self, org_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.memberships.get(org_id, user_id)
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise AuthorizationError("Not an active member of this organization")

    async def _require_permission(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        permission: Permission,
    ) -> None:
        membership = await self.memberships.get(org_id, user_id)
        if membership is None or membership.status != MembershipStatus.ACTIVE:
            raise AuthorizationError("Not an active member of this organization")
        if not membership.has_permission(permission):
            raise AuthorizationError("Insufficient permissions")

    async def _validate_member_ids(
        self,
        org_id: uuid.UUID,
        member_ids: list[uuid.UUID],
    ) -> None:
        if not member_ids:
            return
        org_members = await self.memberships.list_for_org(org_id)
        active_user_ids = {
            item.user_id for item in org_members if item.status == MembershipStatus.ACTIVE
        }
        invalid = [user_id for user_id in member_ids if user_id not in active_user_ids]
        if invalid:
            raise NotFoundError("One or more users are not active organization members")
