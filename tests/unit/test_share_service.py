"""Unit tests for ShareService."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from vaultforge.application.sharing.schemas import (
    AccessControlEntryRequest,
    ReplaceAclRequest,
    ShareGrantCreateRequest,
    ShareLinkCreateRequest,
)
from vaultforge.application.sharing.share_service import ShareService
from vaultforge.core.exceptions import ConflictError, NotFoundError
from vaultforge.domain.sharing.entities import (
    AccessControlEntry,
    ShareGrant,
    ShareInvitation,
    ShareLink,
)
from vaultforge.domain.sharing.enums import (
    SharePermission,
    ShareResourceType,
    ShareStatus,
    ShareTargetType,
)
from vaultforge.domain.sharing.repositories import ShareQueryCriteria


class MemoryGrants:
    def __init__(self) -> None:
        self.items: list[ShareGrant] = []

    async def add(self, grant: ShareGrant) -> ShareGrant:
        self.items.append(grant)
        return grant

    async def update(self, grant: ShareGrant) -> ShareGrant:
        return grant

    async def get_by_id(self, organization_id: uuid.UUID, grant_id: uuid.UUID) -> ShareGrant | None:
        return next((g for g in self.items if g.id == grant_id), None)

    async def query(self, criteria: ShareQueryCriteria) -> Sequence[ShareGrant]:
        return self.items

    async def list_for_resource(self, organization_id, resource_type, resource_id):
        return [g for g in self.items if g.resource_id == resource_id]

    async def list_for_target(self, organization_id, target_id):
        return [g for g in self.items if g.target_id == target_id]


class MemoryLinks:
    def __init__(self) -> None:
        self.items: list[ShareLink] = []

    async def add(self, link: ShareLink) -> ShareLink:
        self.items.append(link)
        return link

    async def update(self, link: ShareLink) -> ShareLink:
        return link

    async def get_by_token(self, token: str) -> ShareLink | None:
        return next((item for item in self.items if item.token == token), None)

    async def get_by_id(self, organization_id, link_id):
        return next((item for item in self.items if item.id == link_id), None)

    async def list_for_resource(self, organization_id, resource_type, resource_id):
        return self.items


class MemoryInvitations:
    def __init__(self) -> None:
        self.items: list[ShareInvitation] = []

    async def add(self, invitation: ShareInvitation) -> ShareInvitation:
        self.items.append(invitation)
        return invitation

    async def update(self, invitation: ShareInvitation) -> ShareInvitation:
        return invitation

    async def get_by_token(self, token: str) -> ShareInvitation | None:
        return next((item for item in self.items if item.token == token), None)

    async def get_by_id(self, organization_id, invitation_id):
        return None


class MemoryAcl:
    def __init__(self) -> None:
        self.entries: list[AccessControlEntry] = []

    async def replace_for_resource(self, organization_id, resource_type, resource_id, entries):
        self.entries = entries
        return entries

    async def list_for_resource(self, organization_id, resource_type, resource_id):
        return self.entries

    async def list_effective_permissions(
        self, organization_id, resource_type, resource_id, principal_id
    ):
        return SharePermission.VIEW


@pytest.fixture
def share_service() -> ShareService:
    return ShareService(MemoryGrants(), MemoryLinks(), MemoryInvitations(), MemoryAcl())


@pytest.mark.asyncio
async def test_create_grant(share_service: ShareService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    resource_id = uuid.uuid4()
    target_id = uuid.uuid4()
    result = await share_service.create_grant(
        org_id,
        actor,
        ShareGrantCreateRequest(
            resource_type=ShareResourceType.DOCUMENT,
            resource_id=resource_id,
            target_type=ShareTargetType.USER,
            target_id=target_id,
            permission=SharePermission.VIEW,
        ),
    )
    assert result.resource_id == resource_id
    assert result.target_id == target_id


@pytest.mark.asyncio
async def test_create_duplicate_grant_raises(share_service: ShareService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    resource_id = uuid.uuid4()
    target_id = uuid.uuid4()
    payload = ShareGrantCreateRequest(
        resource_type=ShareResourceType.DOCUMENT,
        resource_id=resource_id,
        target_type=ShareTargetType.USER,
        target_id=target_id,
    )
    await share_service.create_grant(org_id, actor, payload)
    with pytest.raises(ConflictError):
        await share_service.create_grant(org_id, actor, payload)


@pytest.mark.asyncio
async def test_create_link(share_service: ShareService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    result = await share_service.create_link(
        org_id,
        actor,
        ShareLinkCreateRequest(
            resource_type=ShareResourceType.DOCUMENT,
            resource_id=uuid.uuid4(),
        ),
    )
    assert result.token
    assert result.status == ShareStatus.ACTIVE


@pytest.mark.asyncio
async def test_replace_acl(share_service: ShareService) -> None:
    org_id = uuid.uuid4()
    resource_id = uuid.uuid4()
    principal = uuid.uuid4()
    entries = await share_service.replace_acl(
        org_id,
        ShareResourceType.DOCUMENT,
        resource_id,
        ReplaceAclRequest(
            entries=[
                AccessControlEntryRequest(
                    principal_type=ShareTargetType.USER,
                    principal_id=principal,
                    permission=SharePermission.EDIT,
                )
            ]
        ),
    )
    assert len(entries) == 1


@pytest.mark.asyncio
async def test_revoke_missing_grant(share_service: ShareService) -> None:
    with pytest.raises(NotFoundError):
        await share_service.revoke_grant(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
