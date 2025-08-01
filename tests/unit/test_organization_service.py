"""Unit tests for OrganizationService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.identity.organization_service import OrganizationService
from vaultforge.application.identity.schemas import (
    InviteMemberRequest,
    OrganizationCreate,
    OrganizationUpdate,
)
from vaultforge.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from vaultforge.domain.identity.entities import Membership, Organization, User
from vaultforge.domain.identity.enums import MembershipStatus, OrgRole


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _org(**overrides: object) -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        name="Acme",
        slug="acme",
        created_at=_now(),
        updated_at=_now(),
    )
    for key, value in overrides.items():
        setattr(org, key, value)
    return org


def _membership(role: OrgRole, *, status: MembershipStatus = MembershipStatus.ACTIVE) -> Membership:
    return Membership(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=role,
        status=status,
        created_at=_now(),
        updated_at=_now(),
    )


@pytest.mark.asyncio
async def test_create_organization_adds_owner_membership() -> None:
    org_repo = AsyncMock()
    org_repo.get_by_slug = AsyncMock(return_value=None)
    created_org = _org()
    org_repo.add = AsyncMock(return_value=created_org)
    membership_repo = AsyncMock()
    membership_repo.add = AsyncMock(side_effect=lambda m: m)
    user_repo = AsyncMock()
    service = OrganizationService(org_repo, membership_repo, user_repo)

    creator_id = uuid.uuid4()
    response = await service.create_organization(
        OrganizationCreate(name="Acme", slug="acme-corp"),
        creator_id,
    )

    assert response.slug == "acme"
    membership_repo.add.assert_awaited_once()
    added_membership = membership_repo.add.await_args.args[0]
    assert added_membership.role == OrgRole.OWNER
    assert added_membership.user_id == creator_id


@pytest.mark.asyncio
async def test_create_organization_rejects_duplicate_slug() -> None:
    org_repo = AsyncMock()
    org_repo.get_by_slug = AsyncMock(return_value=_org())
    service = OrganizationService(org_repo, AsyncMock(), AsyncMock())

    with pytest.raises(ConflictError, match="slug"):
        await service.create_organization(
            OrganizationCreate(name="Other", slug="acme"),
            uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_update_organization_requires_org_manage() -> None:
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    membership_repo = AsyncMock()
    membership_repo.get = AsyncMock(return_value=_membership(OrgRole.VIEWER))
    org_repo = AsyncMock()
    service = OrganizationService(org_repo, membership_repo, AsyncMock())

    with pytest.raises(AuthorizationError, match="Insufficient permissions"):
        await service.update_organization(
            org_id,
            OrganizationUpdate(name="Renamed"),
            actor_id,
        )


@pytest.mark.asyncio
async def test_invite_member_creates_invited_membership() -> None:
    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    membership_repo = AsyncMock()
    membership_repo.get = AsyncMock(
        side_effect=[
            _membership(OrgRole.ADMIN),
            None,
        ]
    )
    membership_repo.add = AsyncMock(side_effect=lambda m: m)
    org_repo = AsyncMock()
    org_repo.get_by_id = AsyncMock(return_value=_org(id=org_id))
    user_repo = AsyncMock()
    user_repo.get_by_email = AsyncMock(return_value=None)
    user_repo.add = AsyncMock(
        side_effect=lambda u: User(id=uuid.uuid4(), email=u.email, full_name=u.full_name)
    )
    service = OrganizationService(org_repo, membership_repo, user_repo)

    response = await service.invite_member(
        org_id,
        InviteMemberRequest(email="new@example.com", full_name="New", role=OrgRole.CONTRIBUTOR),
        actor_id,
    )

    assert response.status == MembershipStatus.INVITED
    assert response.role == OrgRole.CONTRIBUTOR


@pytest.mark.asyncio
async def test_get_organization_raises_when_org_missing() -> None:
    org_id = uuid.uuid4()
    membership_repo = AsyncMock()
    membership_repo.get = AsyncMock(return_value=_membership(OrgRole.ADMIN))
    org_repo = AsyncMock()
    org_repo.get_by_id = AsyncMock(return_value=None)
    service = OrganizationService(org_repo, membership_repo, AsyncMock())

    with pytest.raises(NotFoundError):
        await service.get_organization(org_id, uuid.uuid4())
