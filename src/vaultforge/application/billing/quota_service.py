"""Quota enforcement and allocation service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.billing.schemas import QuotaCheckResponse, QuotaStatusResponse
from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.billing.entities import (
    DEFAULT_PLAN_QUOTAS,
    BillingPlan,
    QuotaAllocation,
    QuotaEnforcementResult,
)
from vaultforge.domain.billing.enums import PlanTier, QuotaMetric, QuotaPolicy
from vaultforge.domain.billing.repositories import (
    BillingPlanRepository,
    QuotaAllocationRepository,
    UsageSnapshotRepository,
)
from vaultforge.domain.events import quota_exceeded
from vaultforge.infrastructure.events.event_bus import EventBus


@dataclass(slots=True)
class QuotaService:
    plans: BillingPlanRepository
    allocations: QuotaAllocationRepository
    snapshots: UsageSnapshotRepository
    events: EventBus

    async def ensure_plan(
        self, organization_id: uuid.UUID, tier: PlanTier = PlanTier.FREE
    ) -> BillingPlan:
        plan = await self.plans.get_for_organization(organization_id)
        if plan is not None:
            return plan
        plan = BillingPlan(
            organization_id=organization_id,
            tier=tier,
            quotas=list(DEFAULT_PLAN_QUOTAS[tier]),
        )
        saved = await self.plans.upsert(plan)
        await self._sync_allocations(saved)
        return saved

    async def check_quota(
        self,
        organization_id: uuid.UUID,
        metric: QuotaMetric,
        amount: int,
    ) -> QuotaCheckResponse:
        result = await self._enforce(organization_id, metric, amount)
        return QuotaCheckResponse(
            allowed=result.allowed,
            metric=result.metric,
            requested=result.requested,
            available=result.available,
            message=result.message,
        )

    async def consume_quota(
        self,
        organization_id: uuid.UUID,
        metric: QuotaMetric,
        amount: int,
    ) -> QuotaEnforcementResult:
        result = await self._enforce(organization_id, metric, amount)
        if not result.allowed:
            await self.events.publish(
                quota_exceeded(organization_id, metric.value, result.requested, result.available)
            )
            return result
        allocation = await self._allocation(organization_id, metric)
        allocation.consume(amount)
        await self.allocations.upsert(allocation)
        return result

    async def list_quota_status(self, organization_id: uuid.UUID) -> list[QuotaStatusResponse]:
        await self.ensure_plan(organization_id)
        rows = await self.allocations.list_for_organization(organization_id)
        return [
            QuotaStatusResponse(
                metric=row.metric,
                allocated=row.allocated,
                consumed=row.consumed,
                reserved=row.reserved,
                available=row.available,
                policy=row.policy,
            )
            for row in rows
        ]

    async def _enforce(
        self, organization_id: uuid.UUID, metric: QuotaMetric, amount: int
    ) -> QuotaEnforcementResult:
        if amount < 0:
            raise ValidationError("amount must be non-negative")
        plan = await self.ensure_plan(organization_id)
        limit = plan.quota_for(metric)
        allocation = await self._allocation(organization_id, metric)
        available = allocation.available
        if limit is None:
            return QuotaEnforcementResult.permit(metric, amount, available)
        if limit.policy == QuotaPolicy.HARD and amount > available:
            return QuotaEnforcementResult.deny(
                metric, amount, available, limit.policy, f"{metric.value} quota exceeded"
            )
        return QuotaEnforcementResult.permit(metric, amount, available)

    async def _allocation(self, organization_id: uuid.UUID, metric: QuotaMetric) -> QuotaAllocation:
        row = await self.allocations.get(organization_id, metric)
        if row is not None:
            return row
        plan = await self.ensure_plan(organization_id)
        limit = plan.quota_for(metric)
        allocation = QuotaAllocation(
            organization_id=organization_id,
            metric=metric,
            allocated=limit.limit_value if limit else 0,
            policy=limit.policy if limit else QuotaPolicy.HARD,
        )
        return await self.allocations.upsert(allocation)

    async def _sync_allocations(self, plan: BillingPlan) -> None:
        for quota in plan.quotas:
            allocation = QuotaAllocation(
                organization_id=plan.organization_id,
                metric=quota.metric,
                allocated=quota.limit_value,
                policy=quota.policy,
            )
            await self.allocations.upsert(allocation)
