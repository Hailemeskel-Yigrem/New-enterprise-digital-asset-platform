"""Effective ACL resolver combining RBAC membership and share grants."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from vaultforge.domain.common import utc_now
from vaultforge.domain.identity.entities import Membership
from vaultforge.domain.identity.enums import Permission
from vaultforge.domain.sharing.entities import AccessControlEntry, ShareGrant, merge_acl_entries
from vaultforge.domain.sharing.enums import (
    AclEffect,
    SharePermission,
    ShareResourceType,
    ShareTargetType,
    permission_includes,
)


RBAC_TO_SHARE: dict[Permission, SharePermission] = {
    Permission.DOCUMENT_READ: SharePermission.VIEW,
    Permission.DOCUMENT_UPDATE: SharePermission.EDIT,
    Permission.DOCUMENT_DELETE: SharePermission.DELETE,
    Permission.DOCUMENT_SHARE: SharePermission.SHARE,
}


@dataclass(slots=True)
class PrincipalContext:
    """Caller identity used when evaluating effective permissions."""

    user_id: uuid.UUID
    organization_id: uuid.UUID
    membership: Membership | None = None
    team_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    email: str | None = None


@dataclass(slots=True)
class EffectivePermissionResult:
    allowed: bool
    source: str
    granted: SharePermission | None = None
    deny_reason: str | None = None


class PermissionResolver:
    """Combine organization RBAC, explicit ACL entries, and share grants."""

    def __init__(
        self,
        *,
        acl_entries: list[AccessControlEntry] | None = None,
        share_grants: list[ShareGrant] | None = None,
    ) -> None:
        self._acl_entries = list(acl_entries or [])
        self._share_grants = list(share_grants or [])

    def with_acl(self, entries: list[AccessControlEntry]) -> PermissionResolver:
        return PermissionResolver(
            acl_entries=[*self._acl_entries, *entries],
            share_grants=self._share_grants,
        )

    def with_shares(self, grants: list[ShareGrant]) -> PermissionResolver:
        return PermissionResolver(
            acl_entries=self._acl_entries,
            share_grants=[*self._share_grants, *grants],
        )

    def resolve(
        self,
        principal: PrincipalContext,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        required: SharePermission,
        *,
        at: datetime | None = None,
    ) -> EffectivePermissionResult:
        reference = at or utc_now()

        rbac = self._evaluate_rbac(principal, required)
        if rbac is not None:
            return rbac

        acl_entries = self._matching_acl(principal, resource_type, resource_id)
        if acl_entries:
            allowed = merge_acl_entries(acl_entries, required)
            if not allowed:
                return EffectivePermissionResult(
                    allowed=False,
                    source="acl",
                    deny_reason="Explicit ACL denies access",
                )
            return EffectivePermissionResult(allowed=True, source="acl", granted=required)

        share_perm = self._best_share_permission(
            principal, resource_type, resource_id, reference
        )
        if share_perm is not None and permission_includes(share_perm, required):
            return EffectivePermissionResult(
                allowed=True, source="share", granted=share_perm
            )

        return EffectivePermissionResult(
            allowed=False,
            source="none",
            deny_reason="No matching RBAC, ACL, or share grant",
        )

    def list_effective_permissions(
        self,
        principal: PrincipalContext,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        *,
        at: datetime | None = None,
    ) -> frozenset[SharePermission]:
        granted: set[SharePermission] = set()
        for perm in SharePermission:
            result = self.resolve(
                principal, resource_type, resource_id, perm, at=at
            )
            if result.allowed:
                granted.add(perm)
        return frozenset(granted)

    def _evaluate_rbac(
        self,
        principal: PrincipalContext,
        required: SharePermission,
    ) -> EffectivePermissionResult | None:
        membership = principal.membership
        if membership is None:
            return None

        for permission, share_level in RBAC_TO_SHARE.items():
            if share_level != required:
                continue
            if membership.has_permission(permission):
                return EffectivePermissionResult(
                    allowed=True, source="rbac", granted=share_level
                )
        return None

    def _matching_acl(
        self,
        principal: PrincipalContext,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> list[AccessControlEntry]:
        matches: list[AccessControlEntry] = []
        for entry in self._acl_entries:
            if entry.resource_type != resource_type or entry.resource_id != resource_id:
                continue
            if self._principal_matches(entry, principal):
                matches.append(entry)
        return matches

    def _principal_matches(
        self, entry: AccessControlEntry, principal: PrincipalContext
    ) -> bool:
        if entry.principal_type == ShareTargetType.USER:
            return entry.principal_id == principal.user_id
        if entry.principal_type == ShareTargetType.TEAM:
            return entry.principal_id in principal.team_ids
        if entry.principal_type == ShareTargetType.ORGANIZATION:
            return entry.organization_id == principal.organization_id
        return False

    def _best_share_permission(
        self,
        principal: PrincipalContext,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        at: datetime,
    ) -> SharePermission | None:
        best: SharePermission | None = None
        for grant in self._share_grants:
            if grant.resource_type != resource_type or grant.resource_id != resource_id:
                continue
            if not grant.is_active(at=at):
                continue
            if not self._grant_matches(grant, principal):
                continue
            if best is None or permission_includes(grant.permission, best):
                best = grant.permission
        return best

    def _grant_matches(self, grant: ShareGrant, principal: PrincipalContext) -> bool:
        if grant.target_type == ShareTargetType.USER:
            return grant.target_id == principal.user_id
        if grant.target_type == ShareTargetType.TEAM:
            return grant.target_id in principal.team_ids
        if grant.target_type == ShareTargetType.ORGANIZATION:
            return grant.organization_id == principal.organization_id
        if grant.target_type == ShareTargetType.EXTERNAL_EMAIL:
            return (
                principal.email is not None
                and grant.target_email == principal.email.lower()
            )
        return False


    def explain_access(
        self,
        principal: PrincipalContext,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        required: SharePermission,
        *,
        at: datetime | None = None,
    ) -> "AccessExplanation":
        """Return a step-by-step explanation suitable for audit UI."""
        steps: list[str] = []
        reference = at or utc_now()

        membership = principal.membership
        if membership is not None:
            steps.append(f"Principal has org role {membership.role.value}")
            rbac = self._evaluate_rbac(principal, required)
            if rbac is not None and rbac.allowed:
                steps.append(f"RBAC grants {required.value} via membership")
                return AccessExplanation(True, steps, required)
            steps.append("RBAC does not grant required permission")

        acl_entries = self._matching_acl(principal, resource_type, resource_id)
        if acl_entries:
            steps.append(f"Found {len(acl_entries)} matching ACL entries")
            allowed = merge_acl_entries(acl_entries, required)
            if not allowed:
                steps.append("Explicit ACL denies access")
                return AccessExplanation(False, steps)
            steps.append("ACL allows access")
            return AccessExplanation(True, steps, required)

        share_perm = self._best_share_permission(
            principal, resource_type, resource_id, reference
        )
        if share_perm is not None:
            steps.append(f"Active share grant provides {share_perm.value}")
            if permission_includes(share_perm, required):
                steps.append("Share permission satisfies requirement")
                return AccessExplanation(True, steps, share_perm)
            steps.append("Share permission is insufficient")

        steps.append("No RBAC, ACL, or share grant matched")
        return AccessExplanation(False, steps)

    def resolve_bulk(
        self,
        principal: PrincipalContext,
        resources: list[tuple[ShareResourceType, uuid.UUID]],
        required: SharePermission,
        *,
        at: datetime | None = None,
    ) -> dict[uuid.UUID, EffectivePermissionResult]:
        """Evaluate the same permission against multiple resources."""
        return {
            resource_id: self.resolve(
                principal, resource_type, resource_id, required, at=at
            )
            for resource_type, resource_id in resources
        }


@dataclass(slots=True)
class AccessExplanation:
    """Human-readable breakdown of an access decision."""

    allowed: bool
    steps: list[str]
    effective_permission: SharePermission | None = None


def build_default_deny_entry(
    organization_id: uuid.UUID,
    resource_type: ShareResourceType,
    resource_id: uuid.UUID,
    principal_id: uuid.UUID,
) -> AccessControlEntry:
    """Construct an explicit deny ACE for a principal."""
    return AccessControlEntry(
        organization_id=organization_id,
        resource_type=resource_type,
        resource_id=resource_id,
        principal_type=ShareTargetType.USER,
        principal_id=principal_id,
        permission=SharePermission.ADMIN,
        effect=AclEffect.DENY,
    )
