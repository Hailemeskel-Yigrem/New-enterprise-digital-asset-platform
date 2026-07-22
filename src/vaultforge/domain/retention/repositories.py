"""Retention repository protocols."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from vaultforge.domain.retention.entities import LegalHold, RetentionPolicy, RetentionSchedule
from vaultforge.domain.retention.enums import RetentionScope


@dataclass(slots=True)
class RetentionScheduleQuery:
    organization_id: uuid.UUID
    due_only: bool = False
    resource_id: uuid.UUID | None = None
    limit: int = 200
    offset: int = 0


class RetentionPolicyRepository(Protocol):
    async def add(self, policy: RetentionPolicy) -> RetentionPolicy: ...

    async def update(self, policy: RetentionPolicy) -> RetentionPolicy: ...

    async def get_by_id(
        self, organization_id: uuid.UUID, policy_id: uuid.UUID
    ) -> RetentionPolicy | None: ...

    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> Sequence[RetentionPolicy]: ...

    async def find_applicable(
        self,
        organization_id: uuid.UUID,
        scope: RetentionScope,
        scope_ref_id: uuid.UUID | None,
    ) -> Sequence[RetentionPolicy]: ...


class RetentionScheduleRepository(Protocol):
    async def add(self, schedule: RetentionSchedule) -> RetentionSchedule: ...

    async def update(self, schedule: RetentionSchedule) -> RetentionSchedule: ...

    async def query(self, criteria: RetentionScheduleQuery) -> Sequence[RetentionSchedule]: ...

    async def get_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> RetentionSchedule | None: ...


class LegalHoldRepository(Protocol):
    async def add(self, hold: LegalHold) -> LegalHold: ...

    async def update(self, hold: LegalHold) -> LegalHold: ...

    async def get_by_id(
        self, organization_id: uuid.UUID, hold_id: uuid.UUID
    ) -> LegalHold | None: ...

    async def list_active(self, organization_id: uuid.UUID) -> Sequence[LegalHold]: ...

    async def find_covering_resource(
        self,
        organization_id: uuid.UUID,
        resource_id: uuid.UUID,
        folder_id: uuid.UUID | None = None,
    ) -> Sequence[LegalHold]: ...
