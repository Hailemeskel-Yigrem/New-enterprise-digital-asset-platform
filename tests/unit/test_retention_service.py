"""Unit tests for RetentionService."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from vaultforge.application.retention.retention_service import RetentionService
from vaultforge.application.retention.schemas import (
    LegalHoldCreateRequest,
    RetentionPolicyCreateRequest,
    ScheduleResourceRequest,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError
from vaultforge.domain.retention.entities import LegalHold, RetentionPolicy, RetentionSchedule
from vaultforge.domain.retention.repositories import RetentionScheduleQuery


class MemoryPolicies:
    def __init__(self) -> None:
        self.items: list[RetentionPolicy] = []

    async def add(self, policy: RetentionPolicy) -> RetentionPolicy:
        self.items.append(policy)
        return policy

    async def update(self, policy: RetentionPolicy) -> RetentionPolicy:
        return policy

    async def get_by_id(self, organization_id, policy_id):
        return next((p for p in self.items if p.id == policy_id), None)

    async def list_for_organization(self, organization_id):
        return self.items

    async def find_applicable(self, organization_id, scope, scope_ref_id):
        return [p for p in self.items if p.applies_to(scope, scope_ref_id)]


class MemorySchedules:
    def __init__(self) -> None:
        self.items: list[RetentionSchedule] = []

    async def add(self, schedule: RetentionSchedule) -> RetentionSchedule:
        self.items.append(schedule)
        return schedule

    async def update(self, schedule: RetentionSchedule) -> RetentionSchedule:
        return schedule

    async def query(self, criteria: RetentionScheduleQuery) -> Sequence[RetentionSchedule]:
        return self.items

    async def get_for_resource(self, organization_id, resource_type, resource_id):
        return next((s for s in self.items if s.resource_id == resource_id), None)


class MemoryHolds:
    def __init__(self) -> None:
        self.items: list[LegalHold] = []

    async def add(self, hold: LegalHold) -> LegalHold:
        self.items.append(hold)
        return hold

    async def update(self, hold: LegalHold) -> LegalHold:
        return hold

    async def get_by_id(self, organization_id, hold_id):
        return next((h for h in self.items if h.id == hold_id), None)

    async def list_active(self, organization_id):
        return [h for h in self.items if h.is_active()]

    async def find_covering_resource(self, organization_id, resource_id, folder_id=None):
        return [h for h in self.items if h.covers_resource(resource_id, folder_id)]


@pytest.fixture
def retention_service() -> RetentionService:
    return RetentionService(MemoryPolicies(), MemorySchedules(), MemoryHolds())


@pytest.mark.asyncio
async def test_create_policy(retention_service: RetentionService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    result = await retention_service.create_policy(
        org_id,
        actor,
        RetentionPolicyCreateRequest(name="7 year policy", retention_days=2555),
    )
    assert result.name == "7 year policy"


@pytest.mark.asyncio
async def test_schedule_resource(retention_service: RetentionService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    policy = await retention_service.create_policy(
        org_id, actor, RetentionPolicyCreateRequest(name="Annual", retention_days=365)
    )
    resource_id = uuid.uuid4()
    schedule = await retention_service.schedule_resource(
        org_id,
        policy.id,
        ScheduleResourceRequest(resource_id=resource_id),
    )
    assert schedule.resource_id == resource_id


@pytest.mark.asyncio
async def test_duplicate_schedule_raises(retention_service: RetentionService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    policy = await retention_service.create_policy(
        org_id, actor, RetentionPolicyCreateRequest(name="Annual", retention_days=365)
    )
    resource_id = uuid.uuid4()
    payload = ScheduleResourceRequest(resource_id=resource_id)
    await retention_service.schedule_resource(org_id, policy.id, payload)
    with pytest.raises(ConflictError):
        await retention_service.schedule_resource(org_id, policy.id, payload)


@pytest.mark.asyncio
async def test_create_legal_hold(retention_service: RetentionService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    resource_id = uuid.uuid4()
    hold = await retention_service.create_legal_hold(
        org_id,
        actor,
        LegalHoldCreateRequest(name="Litigation hold", resource_ids=[resource_id]),
    )
    assert resource_id in hold.resource_ids


@pytest.mark.asyncio
async def test_disable_missing_policy(retention_service: RetentionService) -> None:
    with pytest.raises(NotFoundError):
        await retention_service.disable_policy(uuid.uuid4(), uuid.uuid4())
