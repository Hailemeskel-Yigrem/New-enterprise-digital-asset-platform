"""Unit tests for sharing domain entities."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import AuthorizationError, ValidationError
from vaultforge.domain.sharing.entities import (
    AccessControlEntry,
    ShareGrant,
    ShareInvitation,
    ShareLink,
    merge_acl_entries,
)
from vaultforge.domain.sharing.enums import (
    AclEffect,
    SharePermission,
    ShareStatus,
    ShareTargetType,
)


def test_share_grant_requires_target_id() -> None:
    with pytest.raises(ValidationError):
        ShareGrant(target_type=ShareTargetType.USER, target_id=None)


def test_share_grant_external_email() -> None:
    grant = ShareGrant(
        target_type=ShareTargetType.EXTERNAL_EMAIL,
        target_email="Partner@Example.com",
    )
    assert grant.target_email == "partner@example.com"
    assert grant.is_active()


def test_share_grant_revoke() -> None:
    actor = uuid.uuid4()
    grant = ShareGrant(granted_by=actor, target_id=uuid.uuid4())
    grant.revoke(actor)
    assert grant.status == ShareStatus.REVOKED
    assert grant.revoked_by == actor


def test_share_grant_extend_expiry() -> None:
    grant = ShareGrant(status=ShareStatus.EXPIRED, target_id=uuid.uuid4())
    grant.extend_expiry(7)
    assert grant.status == ShareStatus.ACTIVE
    assert grant.expires_at is not None


def test_share_link_max_uses() -> None:
    link = ShareLink(max_uses=1)
    link.record_use()
    with pytest.raises(AuthorizationError):
        link.record_use()


def test_share_invitation_accept() -> None:
    user_id = uuid.uuid4()
    invitation = ShareInvitation(email="user@test.com")
    invitation.accept(user_id)
    assert invitation.accepted_by == user_id
    assert invitation.status == ShareStatus.ACTIVE


def test_merge_acl_deny_overrides() -> None:
    entries = [
        AccessControlEntry(permission=SharePermission.VIEW, effect=AclEffect.ALLOW),
        AccessControlEntry(permission=SharePermission.ADMIN, effect=AclEffect.DENY),
    ]
    assert merge_acl_entries(entries, SharePermission.VIEW) is False


def test_merge_acl_allow() -> None:
    entries = [
        AccessControlEntry(permission=SharePermission.EDIT, effect=AclEffect.ALLOW),
    ]
    assert merge_acl_entries(entries, SharePermission.VIEW) is True
