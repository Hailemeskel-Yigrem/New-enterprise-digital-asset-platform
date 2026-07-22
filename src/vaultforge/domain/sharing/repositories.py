"""Sharing repository protocols."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from vaultforge.domain.sharing.entities import (
    AccessControlEntry,
    ShareGrant,
    ShareInvitation,
    ShareLink,
)
from vaultforge.domain.sharing.enums import SharePermission, ShareResourceType, ShareStatus


@dataclass(slots=True)
class ShareQueryCriteria:
    organization_id: uuid.UUID
    resource_type: ShareResourceType | None = None
    resource_id: uuid.UUID | None = None
    target_id: uuid.UUID | None = None
    status: ShareStatus | None = ShareStatus.ACTIVE
    limit: int = 100
    offset: int = 0


class ShareGrantRepository(Protocol):
    async def add(self, grant: ShareGrant) -> ShareGrant: ...

    async def update(self, grant: ShareGrant) -> ShareGrant: ...

    async def get_by_id(
        self, organization_id: uuid.UUID, grant_id: uuid.UUID
    ) -> ShareGrant | None: ...

    async def query(self, criteria: ShareQueryCriteria) -> Sequence[ShareGrant]: ...

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> Sequence[ShareGrant]: ...

    async def list_for_target(
        self,
        organization_id: uuid.UUID,
        target_id: uuid.UUID,
    ) -> Sequence[ShareGrant]: ...


class ShareLinkRepository(Protocol):
    async def add(self, link: ShareLink) -> ShareLink: ...

    async def update(self, link: ShareLink) -> ShareLink: ...

    async def get_by_token(self, token: str) -> ShareLink | None: ...

    async def get_by_id(
        self, organization_id: uuid.UUID, link_id: uuid.UUID
    ) -> ShareLink | None: ...

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> Sequence[ShareLink]: ...


class ShareInvitationRepository(Protocol):
    async def add(self, invitation: ShareInvitation) -> ShareInvitation: ...

    async def update(self, invitation: ShareInvitation) -> ShareInvitation: ...

    async def get_by_token(self, token: str) -> ShareInvitation | None: ...

    async def get_by_id(
        self, organization_id: uuid.UUID, invitation_id: uuid.UUID
    ) -> ShareInvitation | None: ...


class AccessControlRepository(Protocol):
    async def replace_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        entries: list[AccessControlEntry],
    ) -> list[AccessControlEntry]: ...

    async def list_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
    ) -> Sequence[AccessControlEntry]: ...

    async def list_effective_permissions(
        self,
        organization_id: uuid.UUID,
        resource_type: ShareResourceType,
        resource_id: uuid.UUID,
        principal_id: uuid.UUID,
    ) -> SharePermission | None: ...
