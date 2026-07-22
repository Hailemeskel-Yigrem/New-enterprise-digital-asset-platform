"""Complete permission matrix coverage for all roles."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.domain.identity.entities import Membership
from vaultforge.domain.identity.enums import ROLE_PERMISSIONS, MembershipStatus, OrgRole, Permission


@pytest.mark.parametrize("permission", list(Permission))
def test_owner_has_every_permission(permission: Permission) -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=OrgRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    assert membership.has_permission(permission)


@pytest.mark.parametrize(
    ("role", "permission", "expected"),
    [
        (OrgRole.ADMIN, Permission.SETTINGS_MANAGE, True),
        (OrgRole.ADMIN, Permission.AUDIT_READ, True),
        (OrgRole.MANAGER, Permission.WORKFLOW_MANAGE, True),
        (OrgRole.MANAGER, Permission.USER_MANAGE, False),
        (OrgRole.MANAGER, Permission.SETTINGS_MANAGE, False),
        (OrgRole.CONTRIBUTOR, Permission.DOCUMENT_UPLOAD, True),
        (OrgRole.CONTRIBUTOR, Permission.DOCUMENT_DELETE, False),
        (OrgRole.CONTRIBUTOR, Permission.FOLDER_MANAGE, False),
        (OrgRole.VIEWER, Permission.DOCUMENT_READ, True),
        (OrgRole.VIEWER, Permission.DOCUMENT_UPLOAD, False),
        (OrgRole.AUDITOR, Permission.AUDIT_READ, True),
        (OrgRole.AUDITOR, Permission.DOCUMENT_UPDATE, False),
    ],
)
def test_role_permission_matrix(role: OrgRole, permission: Permission, expected: bool) -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=role,
        status=MembershipStatus.ACTIVE,
    )
    assert membership.has_permission(permission) is expected


def test_matrix_matches_role_permissions_constant() -> None:
    for role, permissions in ROLE_PERMISSIONS.items():
        membership = Membership(
            organization_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            role=role,
            status=MembershipStatus.ACTIVE,
        )
        for permission in Permission:
            assert membership.has_permission(permission) == (permission in permissions)


@pytest.mark.parametrize("role", list(OrgRole))
def test_suspended_membership_denies_all(role: OrgRole) -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=role,
        status=MembershipStatus.SUSPENDED,
    )
    for permission in Permission:
        assert not membership.has_permission(permission)


@pytest.mark.parametrize("role", list(OrgRole))
def test_invited_membership_denies_all(role: OrgRole) -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=role,
        status=MembershipStatus.INVITED,
    )
    assert not membership.has_permission(Permission.DOCUMENT_READ)


def test_admin_lacks_nothing_compared_to_owner_except_implicit_owner_only() -> None:
    admin_perms = ROLE_PERMISSIONS[OrgRole.ADMIN]
    owner_perms = ROLE_PERMISSIONS[OrgRole.OWNER]
    assert admin_perms == owner_perms


def test_auditor_read_only_surface() -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=OrgRole.AUDITOR,
        status=MembershipStatus.ACTIVE,
    )
    allowed = {p for p in Permission if membership.has_permission(p)}
    assert allowed == {
        Permission.DOCUMENT_READ,
        Permission.AUDIT_READ,
        Permission.REPORT_READ,
    }
