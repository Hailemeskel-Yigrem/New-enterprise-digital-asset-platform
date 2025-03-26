"""Organization management application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.identity.schemas import (
    InviteMemberRequest,
    MembershipResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from vaultforge.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from vaultforge.domain.identity.entities import Membership, Organization, User
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole, Permission
from vaultforge.domain.identity.repositories import (
    MembershipRepository,
    OrganizationRepository,
    UserRepository,
)
from vaultforge.infrastructure.security import hash_password


@dataclass(slots=True)
class OrganizationService:
    organizations: OrganizationRepository
    memberships: MembershipRepository
    users: UserRepository

    async def create_organization(
        self,
        payload: OrganizationCreate,
        creator_id: uuid.UUID,
    ) -> OrganizationResponse:
        existing = await self.organizations.get_by_slug(payload.slug)
        if existing is not None:
            raise ConflictError("Organization slug is already taken")

        organization = Organization(
            name=payload.name,
            slug=payload.slug,
            plan_code=payload.plan_code,
            max_storage_gb=payload.max_storage_gb,
        )
        created = await self.organizations.add(organization)

        membership = Membership(
            organization_id=created.id,
            user_id=creator_id,
            role=OrgRole.OWNER,
            status=MembershipStatus.ACTIVE,
        )
        await self.memberships.add(membership)

        return OrganizationResponse.model_validate(created)

    async def list_for_user(self, user_id: uuid.UUID) -> list[OrganizationResponse]:
        orgs = await self.organizations.list_for_user(user_id)
        return [OrganizationResponse.model_validate(org) for org in orgs]

    async def get_organization(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganizationResponse:
        await self._require_membership(org_id, user_id)
        organization = await self.organizations.get_by_id(org_id)
        if organization is None:
            raise NotFoundError("Organization not found")
        return OrganizationResponse.model_validate(organization)

    async def update_organization(
        self,
        org_id: uuid.UUID,
        payload: OrganizationUpdate,
        actor_id: uuid.UUID,
    ) -> OrganizationResponse:
        membership = await self._require_membership(org_id, actor_id)
        if not membership.has_permission(Permission.ORG_MANAGE):
            raise AuthorizationError("Insufficient permissions to update organization")

        organization = await self.organizations.get_by_id(org_id)
        if organization is None:
            raise NotFoundError("Organization not found")

        if payload.name is not None:
            organization.name = payload.name
        if payload.is_active is not None:
            organization.is_active = payload.is_active
        if payload.plan_code is not None:
            organization.plan_code = payload.plan_code
        if payload.max_storage_gb is not None:
            organization.max_storage_gb = payload.max_storage_gb
        organization.touch()

        updated = await self.organizations.update(organization)
        return OrganizationResponse.model_validate(updated)

    async def invite_member(
        self,
        org_id: uuid.UUID,
        payload: InviteMemberRequest,
        actor_id: uuid.UUID,
    ) -> MembershipResponse:
        membership = await self._require_membership(org_id, actor_id)
        if not membership.has_permission(Permission.USER_MANAGE):
            raise AuthorizationError("Insufficient permissions to invite members")

        organization = await self.organizations.get_by_id(org_id)
        if organization is None:
            raise NotFoundError("Organization not found")

        user = await self.users.get_by_email(payload.email)
        if user is None:
            user = User(
                email=payload.email.lower(),
                full_name=payload.full_name,
                password_hash=hash_password(uuid.uuid4().hex),
                is_active=False,
                is_email_verified=False,
            )
            user = await self.users.add(user)

        existing_membership = await self.memberships.get(org_id, user.id)
        if existing_membership is not None:
            if existing_membership.status == MembershipStatus.REMOVED:
                existing_membership.status = MembershipStatus.INVITED
                existing_membership.role = payload.role
                existing_membership.touch()
                updated = await self.memberships.update(existing_membership)
                return MembershipResponse.model_validate(updated)
            raise ConflictError("User is already a member of this organization")

        invited = Membership(
            organization_id=org_id,
            user_id=user.id,
            role=payload.role,
            status=MembershipStatus.INVITED,
        )
        created = await self.memberships.add(invited)
        return MembershipResponse.model_validate(created)

    async def list_members(
        self,
        org_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> list[MembershipResponse]:
        membership = await self._require_membership(org_id, actor_id)
        if not membership.has_permission(Permission.USER_MANAGE):
            raise AuthorizationError("Insufficient permissions to list members")

        members = await self.memberships.list_for_org(org_id)
        return [MembershipResponse.model_validate(item) for item in members]

    async def _require_membership(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Membership:
        membership = await self.memberships.get(org_id, user_id)
        if membership is None or membership.status == MembershipStatus.REMOVED:
            raise AuthorizationError("Not a member of this organization")
        if membership.status != MembershipStatus.ACTIVE:
            raise AuthorizationError("Membership is not active")
        return membership
