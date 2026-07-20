"""Billing repository interfaces."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence

from vaultforge.domain.billing.entities import (
    BillingPlan,
    QuotaAllocation,
    UsageRecord,
    UsageSnapshot,
)
from vaultforge.domain.billing.enums import QuotaMetric


class BillingPlanRepository(ABC):
    @abstractmethod
    async def get_for_organization(self, organization_id: uuid.UUID) -> BillingPlan | None: ...

    @abstractmethod
    async def upsert(self, plan: BillingPlan) -> BillingPlan: ...


class UsageRecordRepository(ABC):
    @abstractmethod
    async def append(self, record: UsageRecord) -> UsageRecord: ...

    @abstractmethod
    async def list_for_period(
        self,
        organization_id: uuid.UUID,
        *,
        metric: QuotaMetric | None = None,
        limit: int = 500,
    ) -> Sequence[UsageRecord]: ...


class UsageSnapshotRepository(ABC):
    @abstractmethod
    async def get_current(self, organization_id: uuid.UUID) -> UsageSnapshot | None: ...

    @abstractmethod
    async def upsert(self, snapshot: UsageSnapshot) -> UsageSnapshot: ...


class QuotaAllocationRepository(ABC):
    @abstractmethod
    async def get(
        self, organization_id: uuid.UUID, metric: QuotaMetric
    ) -> QuotaAllocation | None: ...

    @abstractmethod
    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> Sequence[QuotaAllocation]: ...

    @abstractmethod
    async def upsert(self, allocation: QuotaAllocation) -> QuotaAllocation: ...
