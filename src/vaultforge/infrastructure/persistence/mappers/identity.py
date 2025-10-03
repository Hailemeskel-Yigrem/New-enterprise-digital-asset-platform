"""Mappers between identity domain entities and persistence models."""

from __future__ import annotations

import uuid

from vaultforge.domain.identity.entities import Membership, Organization, Team, User
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole
from vaultforge.infrastructure.persistence.models.membership import MembershipModel
from vaultforge.infrastructure.persistence.models.organization import OrganizationModel
from vaultforge.infrastructure.persistence.models.team import TeamMemberModel, TeamModel
from vaultforge.infrastructure.persistence.models.user import UserModel


def user_to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        email=entity.email,
        full_name=entity.full_name,
        password_hash=entity.password_hash,
        is_active=entity.is_active,
        is_email_verified=entity.is_email_verified,
        last_login_at=entity.last_login_at,  # type: ignore[arg-type]
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def user_from_model(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        full_name=model.full_name,
        password_hash=model.password_hash,
        is_active=model.is_active,
        is_email_verified=model.is_email_verified,
        last_login_at=model.last_login_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def organization_to_model(entity: Organization) -> OrganizationModel:
    return OrganizationModel(
        id=entity.id,
        name=entity.name,
        slug=entity.slug,
        is_active=entity.is_active,
        plan_code=entity.plan_code,
        max_storage_gb=entity.max_storage_gb,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def organization_from_model(model: OrganizationModel) -> Organization:
    return Organization(
        id=model.id,
        name=model.name,
        slug=model.slug,
        is_active=model.is_active,
        plan_code=model.plan_code,
        max_storage_gb=model.max_storage_gb,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def membership_to_model(entity: Membership) -> MembershipModel:
    return MembershipModel(
        id=entity.id,
        organization_id=entity.organization_id,
        user_id=entity.user_id,
        role=entity.role.value,
        status=entity.status.value,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def membership_from_model(model: MembershipModel) -> Membership:
    return Membership(
        id=model.id,
        organization_id=model.organization_id,
        user_id=model.user_id,
        role=OrgRole(model.role),
        status=MembershipStatus(model.status),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def team_to_model(entity: Team) -> TeamModel:
    return TeamModel(
        id=entity.id,
        organization_id=entity.organization_id,
        name=entity.name,
        description=entity.description,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def team_from_model(model: TeamModel, *, member_ids: list[uuid.UUID] | None = None) -> Team:
    return Team(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        member_ids=list(member_ids or []),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def team_member_to_model(team_id: uuid.UUID, user_id: uuid.UUID) -> TeamMemberModel:
    return TeamMemberModel(team_id=team_id, user_id=user_id)

def users_from_models(models: list[UserModel]) -> list[User]:
    return [user_from_model(m) for m in models]


def users_to_models(entities: list[User]) -> list[UserModel]:
    return [user_to_model(e) for e in entities]


def memberships_from_models(models: list[MembershipModel]) -> list[Membership]:
    return [membership_from_model(m) for m in models]


def teams_from_models(
    models: list[TeamModel],
    *,
    members_by_team: dict[uuid.UUID, list[uuid.UUID]] | None = None,
) -> list[Team]:
    lookup = members_by_team or {}
    return [team_from_model(m, member_ids=lookup.get(m.id, [])) for m in models]


def merge_user_patch(model: UserModel, entity: User) -> UserModel:
    """Apply domain entity fields onto an existing ORM model."""
    model.email = entity.email
    model.full_name = entity.full_name
    model.is_active = entity.is_active
    model.is_email_verified = entity.is_email_verified
    model.last_login_at = entity.last_login_at  # type: ignore[assignment]
    model.updated_at = entity.updated_at
    return model
