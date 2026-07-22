"""Repository interfaces for audit and activity."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from vaultforge.domain.audit.entities import ActivityItem, AuditEvent


@dataclass(frozen=True, slots=True)
class AuditQueryCriteria:
    organization_id: uuid.UUID
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class ActivityQueryCriteria:
    organization_id: uuid.UUID
    user_id: uuid.UUID | None = None
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = 50
    offset: int = 0


class AuditEventRepository(ABC):
    @abstractmethod
    async def add(self, event: AuditEvent) -> AuditEvent: ...

    @abstractmethod
    async def query(self, criteria: AuditQueryCriteria) -> Sequence[AuditEvent]: ...


class ActivityItemRepository(ABC):
    @abstractmethod
    async def add(self, item: ActivityItem) -> ActivityItem: ...

    @abstractmethod
    async def query(self, criteria: ActivityQueryCriteria) -> Sequence[ActivityItem]: ...
