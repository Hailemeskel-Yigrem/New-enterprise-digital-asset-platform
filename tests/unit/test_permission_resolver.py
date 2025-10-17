"""Unit tests for effective permission resolution."""

from __future__ import annotations

import uuid

from vaultforge.application.assets.permission_resolver import (
    PermissionResolver,
    PrincipalContext,
    build_default_deny_entry,
)
from vaultforge.domain.identity.entities import Membership
from vaultforge.domain.identity.enums import OrgRole, Permission
from vaultforge.domain.sharing.entities import AccessControlEntry, ShareGrant
from vaultforge.domain.sharing.enums import (
    AclEffect,
    SharePermission,
    ShareResourceType,
    ShareStatus,
    ShareTargetType,
)


def _principal(*, role: OrgRole = OrgRole.VIEWER) -> PrincipalContext:
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    return PrincipalContext(
        user_id=user_id,
        organization_id=org_id,
        membership=Membership(
            organization_id=org_id,
            user_id=user_id,
            role=role,
        ),
    )


def test_rbac_viewer_can_view_documents() -> None:
    principal = _principal(role=OrgRole.VIEWER)
    resolver = PermissionResolver()
    resource_id = uuid.uuid4()
    result = resolver.resolve(
        principal,
        ShareResourceType.DOCUMENT,
        resource_id,
        SharePermission.VIEW,
    )
    assert result.allowed is True
    assert result.source == "rbac"


def test_rbac_viewer_cannot_delete_without_share() -> None:
    principal = _principal(role=OrgRole.VIEWER)
    resolver = PermissionResolver()
    result = resolver.resolve(
        principal,
        ShareResourceType.DOCUMENT,
        uuid.uuid4(),
        SharePermission.DELETE,
    )
    assert result.allowed is False


def test_share_grant_overrides_missing_rbac() -> None:
    principal = PrincipalContext(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        membership=None,
    )
    resource_id = uuid.uuid4()
    grant = ShareGrant(
        organization_id=principal.organization_id,
        resource_type=ShareResourceType.DOCUMENT,
        resource_id=resource_id,
        target_type=ShareTargetType.USER,
        target_id=principal.user_id,
        permission=SharePermission.EDIT,
        granted_by=uuid.uuid4(),
        status=ShareStatus.ACTIVE,
    )
    resolver = PermissionResolver(share_grants=[grant])
    result = resolver.resolve(
        principal,
        ShareResourceType.DOCUMENT,
        resource_id,
        SharePermission.EDIT,
    )
    assert result.allowed is True
    assert result.source == "share"


def test_acl_deny_blocks_even_with_share() -> None:
    principal = _principal(role=OrgRole.ADMIN)
    resource_id = uuid.uuid4()
    deny = build_default_deny_entry(
        principal.organization_id,
        ShareResourceType.DOCUMENT,
        resource_id,
        principal.user_id,
    )
    grant = ShareGrant(
        organization_id=principal.organization_id,
        resource_type=ShareResourceType.DOCUMENT,
        resource_id=resource_id,
        target_type=ShareTargetType.USER,
        target_id=principal.user_id,
        permission=SharePermission.ADMIN,
    )
    resolver = PermissionResolver(acl_entries=[deny], share_grants=[grant])
    result = resolver.resolve(
        principal,
        ShareResourceType.DOCUMENT,
        resource_id,
        SharePermission.VIEW,
    )
    assert result.allowed is False
    assert result.source == "acl"


def test_list_effective_permissions_includes_edit_for_contributor() -> None:
    principal = _principal(role=OrgRole.CONTRIBUTOR)
    resolver = PermissionResolver()
    perms = resolver.list_effective_permissions(
        principal,
        ShareResourceType.DOCUMENT,
        uuid.uuid4(),
    )
    assert SharePermission.EDIT in perms
    assert SharePermission.DELETE not in perms


def test_team_share_grant_matches_team_membership() -> None:
    user_id = uuid.uuid4()
    team_id = uuid.uuid4()
    org_id = uuid.uuid4()
    resource_id = uuid.uuid4()
    principal = PrincipalContext(
        user_id=user_id,
        organization_id=org_id,
        team_ids=frozenset({team_id}),
    )
    grant = ShareGrant(
        organization_id=org_id,
        resource_type=ShareResourceType.FOLDER,
        resource_id=resource_id,
        target_type=ShareTargetType.TEAM,
        target_id=team_id,
        permission=SharePermission.DOWNLOAD,
    )
    resolver = PermissionResolver(share_grants=[grant])
    result = resolver.resolve(
        principal,
        ShareResourceType.FOLDER,
        resource_id,
        SharePermission.DOWNLOAD,
    )
    assert result.allowed is True

def test_explain_access_denied_without_membership() -> None:
    principal = PrincipalContext(user_id=uuid.uuid4(), organization_id=uuid.uuid4())
    resolver = PermissionResolver()
    explanation = resolver.explain_access(
        principal,
        ShareResourceType.DOCUMENT,
        uuid.uuid4(),
        SharePermission.VIEW,
    )
    assert explanation.allowed is False
    assert any("No RBAC" in step for step in explanation.steps)


def test_resolve_bulk_returns_map() -> None:
    principal = _principal(role=OrgRole.VIEWER)
    resolver = PermissionResolver()
    ids = [uuid.uuid4(), uuid.uuid4()]
    resources = [(ShareResourceType.DOCUMENT, i) for i in ids]
    results = resolver.resolve_bulk(principal, resources, SharePermission.VIEW)
    assert len(results) == 2
    assert all(r.allowed for r in results.values())
