"""Unit tests for role-based access control."""

from __future__ import annotations

import uuid

from vaultforge.domain.identity.entities import Membership
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole, Permission


def test_owner_has_all_permissions() -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=OrgRole.OWNER,
        status=MembershipStatus.ACTIVE,
    )
    for permission in Permission:
        assert membership.has_permission(permission)


def test_viewer_can_only_read_documents() -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=OrgRole.VIEWER,
        status=MembershipStatus.ACTIVE,
    )
    assert membership.has_permission(Permission.DOCUMENT_READ)
    assert not membership.has_permission(Permission.DOCUMENT_UPLOAD)
    assert not membership.has_permission(Permission.USER_MANAGE)


def test_inactive_membership_has_no_permissions() -> None:
    membership = Membership(
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=OrgRole.ADMIN,
        status=MembershipStatus.SUSPENDED,
    )
    assert not membership.has_permission(Permission.ORG_MANAGE)
