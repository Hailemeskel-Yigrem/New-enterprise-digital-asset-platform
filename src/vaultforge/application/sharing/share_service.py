"""Sharing and access-control application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.sharing.schemas import (
    AccessControlEntryResponse,
    ReplaceAclRequest,
    ShareAccessCheckRequest,
    ShareAccessCheckResponse,
    ShareGrantCreateRequest,
    ShareGrantResponse,
    ShareInvitationCreateRequest,
    ShareInvitationResponse,
    ShareLinkCreateRequest,
    ShareLinkResponse,
)
from vaultforge.core.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from vaultforge.domain.sharing.entities import (
    AccessControlEntry,
    ShareGrant,
    ShareInvitation,
    ShareLink,
    merge_acl_entries,
)
from vaultforge.domain.sharing.enums import (
    SharePermission,
    ShareResourceType,
    ShareStatus,
    ShareTargetType,
)
from vaultforge.domain.sharing.repositories import (
    AccessControlRepository,
    ShareGrantRepository,
    ShareInvitationRepository,
    ShareLinkRepository,
    ShareQueryCriteria,
)
from vaultforge.infrastructure.security.password import hash_password, verify_password


@dataclass(slots=True)
class ShareService:
    grants: ShareGrantRepository
    links: ShareLinkRepository
    invitations: ShareInvitationRepository
    acl: AccessControlRepository

    async def create_grant(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ShareGrantCreateRequest,
    ) -> ShareGrantResponse:
        existing = await self.grants.list_for_resource(
            organization_id, payload.resource_type, payload.resource_id
        )
        for grant in existing:
            if (
                grant.target_type == payload.target_type
                and grant.target_id == payload.target_id
                and grant.target_email
                == (str(payload.target_email) if payload.target_email else None)
                and grant.is_active()
            ):
                raise ConflictError("An active share already exists for this target")

        grant = ShareGrant(
            organization_id=organization_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            target_type=payload.target_type,
            target_id=payload.target_id,
            target_email=str(payload.target_email) if payload.target_email else None,
            permission=payload.permission,
            granted_by=actor_id,
            expires_at=payload.expires_at,
            message=payload.message,
        )
        saved = await self.grants.add(grant)
        return ShareGrantResponse.model_validate(saved)

    async def revoke_grant(
        self,
        organization_id: uuid.UUID,
        grant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> ShareGrantResponse:
        grant = await self._get_grant(organization_id, grant_id)
        grant.revoke(actor_id)
        saved = await self.grants.update(grant)
        return ShareGrantResponse.model_validate(saved)

    async def list_grants(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> list[ShareGrantResponse]:
        grants = await self.grants.list_for_resource(organization_id, resource_type, resource_id)
        return [ShareGrantResponse.model_validate(g) for g in grants]

    async def create_link(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ShareLinkCreateRequest,
    ) -> ShareLinkResponse:
        link = ShareLink(
            organization_id=organization_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            permission=payload.permission,
            created_by=actor_id,
            password_hash=hash_password(payload.password) if payload.password else None,
            max_uses=payload.max_uses,
            expires_at=payload.expires_at,
        )
        saved = await self.links.add(link)
        return ShareLinkResponse.model_validate(saved)

    async def revoke_link(
        self,
        organization_id: uuid.UUID,
        link_id: uuid.UUID,
    ) -> ShareLinkResponse:
        link = await self._get_link(organization_id, link_id)
        link.revoke()
        saved = await self.links.update(link)
        return ShareLinkResponse.model_validate(saved)

    async def access_via_link(
        self,
        token: str,
        *,
        password: str | None = None,
        required: SharePermission = SharePermission.VIEW,
    ) -> ShareLinkResponse:
        link = await self.links.get_by_token(token)
        if link is None:
            raise NotFoundError("Share link not found")
        if not link.is_usable():
            raise AuthorizationError("Share link is expired or revoked")
        if link.password_hash is not None and (
            password is None or not verify_password(password, link.password_hash)
        ):
            raise AuthorizationError("Invalid share link password")
        if not link.permission or not _permission_includes(link.permission, required):
            raise AuthorizationError("Insufficient share link permission")
        link.record_use()
        await self.links.update(link)
        return ShareLinkResponse.model_validate(link)

    async def create_invitation(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ShareInvitationCreateRequest,
    ) -> ShareInvitationResponse:
        invitation = ShareInvitation(
            organization_id=organization_id,
            resource_type=payload.resource_type,
            resource_id=payload.resource_id,
            email=str(payload.email),
            permission=payload.permission,
            invited_by=actor_id,
            expires_at=payload.expires_at,
        )
        saved = await self.invitations.add(invitation)
        return ShareInvitationResponse.model_validate(saved)

    async def accept_invitation(
        self,
        token: str,
        user_id: uuid.UUID,
    ) -> ShareInvitationResponse:
        invitation = await self.invitations.get_by_token(token)
        if invitation is None:
            raise NotFoundError("Invitation not found")
        invitation.accept(user_id)
        saved = await self.invitations.update(invitation)
        grant = ShareGrant(
            organization_id=saved.organization_id,
            resource_type=saved.resource_type,
            resource_id=saved.resource_id,
            target_type=ShareTargetType.USER,
            target_id=user_id,
            permission=saved.permission,
            granted_by=saved.invited_by,
        )
        await self.grants.add(grant)
        return ShareInvitationResponse.model_validate(saved)

    async def replace_acl(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        payload: ReplaceAclRequest,
    ) -> list[AccessControlEntryResponse]:
        entries = [
            AccessControlEntry(
                organization_id=organization_id,
                resource_type=resource_type,
                resource_id=resource_id,
                principal_type=item.principal_type,
                principal_id=item.principal_id,
                permission=item.permission,
                effect=item.effect,
            )
            for item in payload.entries
        ]
        saved = await self.acl.replace_for_resource(
            organization_id, resource_type, resource_id, entries
        )
        return [AccessControlEntryResponse.model_validate(e) for e in saved]

    async def list_acl(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> list[AccessControlEntryResponse]:
        entries = await self.acl.list_for_resource(organization_id, resource_type, resource_id)
        return [AccessControlEntryResponse.model_validate(e) for e in entries]

    async def check_access(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ShareAccessCheckRequest,
    ) -> ShareAccessCheckResponse:
        acl_entries = list(
            await self.acl.list_for_resource(
                organization_id, payload.resource_type, payload.resource_id
            )
        )
        user_entries = [e for e in acl_entries if e.principal_id == user_id]
        if user_entries and merge_acl_entries(user_entries, payload.permission):
            perm = await self.acl.list_effective_permissions(
                organization_id,
                payload.resource_type,
                payload.resource_id,
                user_id,
            )
            return ShareAccessCheckResponse(allowed=True, effective_permission=perm)

        grants = await self.grants.list_for_target(organization_id, user_id)
        for grant in grants:
            if (
                grant.resource_type == payload.resource_type
                and grant.resource_id == payload.resource_id
                and grant.allows(payload.permission)
            ):
                return ShareAccessCheckResponse(
                    allowed=True,
                    effective_permission=grant.permission,
                    via_share_id=grant.id,
                )

        return ShareAccessCheckResponse(allowed=False)

    async def list_shared_with_user(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> list[ShareGrantResponse]:
        criteria = ShareQueryCriteria(
            organization_id=organization_id,
            target_id=user_id,
            status=ShareStatus.ACTIVE,
        )
        grants = await self.grants.query(criteria)
        return [ShareGrantResponse.model_validate(g) for g in grants if g.is_active()]

    async def extend_grant(
        self,
        organization_id: uuid.UUID,
        grant_id: uuid.UUID,
        days: int,
    ) -> ShareGrantResponse:
        grant = await self._get_grant(organization_id, grant_id)
        grant.extend_expiry(days)
        saved = await self.grants.update(grant)
        return ShareGrantResponse.model_validate(saved)

    async def _get_grant(self, organization_id: uuid.UUID, grant_id: uuid.UUID) -> ShareGrant:
        grant = await self.grants.get_by_id(organization_id, grant_id)
        if grant is None:
            raise NotFoundError("Share grant not found")
        return grant

    async def _get_link(self, organization_id: uuid.UUID, link_id: uuid.UUID) -> ShareLink:
        link = await self.links.get_by_id(organization_id, link_id)
        if link is None:
            raise NotFoundError("Share link not found")
        return link


def _permission_includes(granted: SharePermission, required: SharePermission) -> bool:
    from vaultforge.domain.sharing.enums import permission_includes

    return permission_includes(granted, required)
