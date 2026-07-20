"""Unit tests for in-memory billing repositories."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.domain.billing.entities import BillingPlan, QuotaAllocation, UsageSnapshot
from vaultforge.domain.billing.enums import PlanTier, QuotaMetric
from vaultforge.infrastructure.persistence.repositories.in_memory_billing import (
    InMemoryBillingPlanRepository,
    InMemoryQuotaAllocationRepository,
    InMemoryUsageSnapshotRepository,
)


@pytest.mark.asyncio
async def test_billing_plan_upsert() -> None:
    repo = InMemoryBillingPlanRepository()
    org_id = uuid.uuid4()
    plan = BillingPlan(organization_id=org_id, tier=PlanTier.STARTER)
    saved = await repo.upsert(plan)
    assert await repo.get_for_organization(org_id) == saved


@pytest.mark.asyncio
async def test_quota_allocation_upsert() -> None:
    repo = InMemoryQuotaAllocationRepository()
    org_id = uuid.uuid4()
    allocation = QuotaAllocation(organization_id=org_id, metric=QuotaMetric.SEATS, allocated=10)
    await repo.upsert(allocation)
    loaded = await repo.get(org_id, QuotaMetric.SEATS)
    assert loaded is not None
    assert loaded.allocated == 10


@pytest.mark.asyncio
async def test_usage_snapshot_upsert() -> None:
    repo = InMemoryUsageSnapshotRepository()
    org_id = uuid.uuid4()
    snapshot = UsageSnapshot(organization_id=org_id)
    await repo.upsert(snapshot)
    assert await repo.get_current(org_id) is not None
