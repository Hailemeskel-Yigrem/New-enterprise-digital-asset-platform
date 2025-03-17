"""Repository interfaces for identity aggregates."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Sequence

from vaultforge.domain.identity.entities import Membership, Organization, Team, User


class OrganizationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Organization | None: ...

    @abstractmethod
    async def add(self, organization: Organization) -> Organization: ...

    @abstractmethod
    async def update(self, organization: Organization) -> Organization: ...

    @abstractmethod
    async def list_for_user(self, user_id: uuid.UUID) -> Sequence[Organization]: ...


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def add(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...


class MembershipRepository(ABC):
    @abstractmethod
    async def get(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None: ...

    @abstractmethod
    async def add(self, membership: Membership) -> Membership: ...

    @abstractmethod
    async def update(self, membership: Membership) -> Membership: ...

    @abstractmethod
    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Membership]: ...


class TeamRepository(ABC):
    @abstractmethod
    async def get_by_id(self, team_id: uuid.UUID) -> Team | None: ...

    @abstractmethod
    async def add(self, team: Team) -> Team: ...

    @abstractmethod
    async def list_for_org(self, organization_id: uuid.UUID) -> Sequence[Team]: ...

    @abstractmethod
    async def add_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> Team: ...
