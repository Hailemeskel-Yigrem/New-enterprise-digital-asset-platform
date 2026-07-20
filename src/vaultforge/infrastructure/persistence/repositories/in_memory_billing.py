"""In-memory billing repositories for tests and lightweight deployments."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from vaultforge.domain.billing.entities import (
    BillingPlan,
    QuotaAllocation,
    UsageRecord,
    UsageSnapshot,
)
from vaultforge.domain.billing.enums import QuotaMetric
from vaultforge.domain.billing.repositories import (
    BillingPlanRepository,
    QuotaAllocationRepository,
    UsageRecordRepository,
    UsageSnapshotRepository,
)


class InMemoryBillingPlanRepository(BillingPlanRepository):
    def __init__(self) -> None:
        self._plans: dict[uuid.UUID, BillingPlan] = {}

    async def get_for_organization(self, organization_id: uuid.UUID) -> BillingPlan | None:
        return self._plans.get(organization_id)

    async def upsert(self, plan: BillingPlan) -> BillingPlan:
        self._plans[plan.organization_id] = plan
        return plan


class InMemoryUsageRecordRepository(UsageRecordRepository):
    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    async def append(self, record: UsageRecord) -> UsageRecord:
        self._records.append(record)
        return record

    async def list_for_period(
        self,
        organization_id: uuid.UUID,
        *,
        metric: QuotaMetric | None = None,
        limit: int = 500,
    ) -> Sequence[UsageRecord]:
        rows = [r for r in self._records if r.organization_id == organization_id]
        if metric is not None:
            rows = [r for r in rows if r.metric == metric]
        return rows[:limit]


class InMemoryUsageSnapshotRepository(UsageSnapshotRepository):
    def __init__(self) -> None:
        self._snapshots: dict[uuid.UUID, UsageSnapshot] = {}

    async def get_current(self, organization_id: uuid.UUID) -> UsageSnapshot | None:
        return self._snapshots.get(organization_id)

    async def upsert(self, snapshot: UsageSnapshot) -> UsageSnapshot:
        self._snapshots[snapshot.organization_id] = snapshot
        return snapshot


class InMemoryQuotaAllocationRepository(QuotaAllocationRepository):
    def __init__(self) -> None:
        self._rows: dict[tuple[uuid.UUID, QuotaMetric], QuotaAllocation] = {}

    async def get(self, organization_id: uuid.UUID, metric: QuotaMetric) -> QuotaAllocation | None:
        return self._rows.get((organization_id, metric))

    async def list_for_organization(self, organization_id: uuid.UUID) -> Sequence[QuotaAllocation]:
        return [v for (org, _), v in self._rows.items() if org == organization_id]

    async def upsert(self, allocation: QuotaAllocation) -> QuotaAllocation:
        self._rows[(allocation.organization_id, allocation.metric)] = allocation
        return allocation
