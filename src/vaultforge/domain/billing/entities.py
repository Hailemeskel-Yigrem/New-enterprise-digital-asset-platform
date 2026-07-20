"""Billing plan, usage, and quota domain entities."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.billing.enums import (
    BillingCycle,
    PlanTier,
    QuotaMetric,
    QuotaPolicy,
    UsageEventType,
)
from vaultforge.domain.common import Entity, utc_now


@dataclass(frozen=True, slots=True)
class QuotaLimit:
    metric: QuotaMetric
    limit_value: int
    policy: QuotaPolicy = QuotaPolicy.HARD
    overage_rate_cents: int = 0

    def __post_init__(self) -> None:
        if self.limit_value < 0:
            raise ValidationError("Quota limit cannot be negative")
        if self.policy == QuotaPolicy.OVERAGE_BILLING and self.overage_rate_cents <= 0:
            raise ValidationError("Overage billing requires positive overage_rate_cents")


@dataclass(slots=True)
class BillingPlan(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    tier: PlanTier = PlanTier.FREE
    cycle: BillingCycle = BillingCycle.MONTHLY
    name: str = ""
    is_active: bool = True
    quotas: list[QuotaLimit] = field(default_factory=list)
    seat_count: int = 1
    renews_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            self.name = self.tier.value.replace("_", " ").title()
        if self.seat_count < 1:
            raise ValidationError("seat_count must be at least 1")

    def quota_for(self, metric: QuotaMetric) -> QuotaLimit | None:
        for quota in self.quotas:
            if quota.metric == metric:
                return quota
        return None

    def upgrade(self, tier: PlanTier, quotas: list[QuotaLimit]) -> None:
        self.tier = tier
        self.quotas = quotas
        self.touch()

    def set_renewal(self, days: int = 30) -> None:
        self.renews_at = utc_now() + timedelta(days=days)
        self.touch()


@dataclass(slots=True)
class UsageRecord(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    metric: QuotaMetric = QuotaMetric.STORAGE_BYTES
    event_type: UsageEventType = UsageEventType.STORAGE_DELTA
    delta: int = 0
    absolute_value: int | None = None
    resource_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.delta == 0 and self.absolute_value is None:
            raise ValidationError("Usage record requires delta or absolute_value")


@dataclass(slots=True)
class UsageSnapshot(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    period_start: datetime = field(default_factory=utc_now)
    period_end: datetime = field(default_factory=utc_now)
    totals: dict[str, int] = field(default_factory=dict)

    def set_total(self, metric: QuotaMetric, value: int) -> None:
        if value < 0:
            raise ValidationError("Usage total cannot be negative")
        self.totals[metric.value] = value
        self.touch()

    def get_total(self, metric: QuotaMetric) -> int:
        return self.totals.get(metric.value, 0)

    def increment(self, metric: QuotaMetric, delta: int) -> int:
        current = self.get_total(metric)
        new_value = current + delta
        if new_value < 0:
            raise ValidationError("Usage cannot go negative")
        self.totals[metric.value] = new_value
        self.touch()
        return new_value


@dataclass(slots=True)
class QuotaAllocation(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    metric: QuotaMetric = QuotaMetric.STORAGE_BYTES
    allocated: int = 0
    consumed: int = 0
    reserved: int = 0
    policy: QuotaPolicy = QuotaPolicy.HARD

    @property
    def available(self) -> int:
        return max(0, self.allocated - self.consumed - self.reserved)

    def reserve(self, amount: int) -> None:
        if amount < 0:
            raise ValidationError("Reserve amount must be non-negative")
        if self.policy == QuotaPolicy.HARD and amount > self.available:
            raise ValidationError("Insufficient quota available")
        self.reserved += amount
        self.touch()

    def release_reservation(self, amount: int) -> None:
        self.reserved = max(0, self.reserved - amount)
        self.touch()

    def consume(self, amount: int) -> None:
        if amount < 0:
            raise ValidationError("Consume amount must be non-negative")
        if self.policy == QuotaPolicy.HARD and amount > self.available + self.reserved:
            raise ValidationError("Quota exceeded")
        if amount <= self.reserved:
            self.reserved -= amount
        else:
            remainder = amount - self.reserved
            self.reserved = 0
            self.consumed += remainder
        self.touch()

    def refund(self, amount: int) -> None:
        self.consumed = max(0, self.consumed - amount)
        self.touch()


@dataclass(frozen=True, slots=True)
class QuotaEnforcementResult:
    allowed: bool
    metric: QuotaMetric
    requested: int
    available: int
    policy: QuotaPolicy
    message: str = ""

    @classmethod
    def permit(cls, metric: QuotaMetric, requested: int, available: int) -> QuotaEnforcementResult:
        return cls(
            allowed=True,
            metric=metric,
            requested=requested,
            available=available,
            policy=QuotaPolicy.HARD,
        )

    @classmethod
    def deny(
        cls,
        metric: QuotaMetric,
        requested: int,
        available: int,
        policy: QuotaPolicy,
        message: str,
    ) -> QuotaEnforcementResult:
        return cls(
            allowed=False,
            metric=metric,
            requested=requested,
            available=available,
            policy=policy,
            message=message,
        )


DEFAULT_PLAN_QUOTAS: dict[PlanTier, list[QuotaLimit]] = {
    PlanTier.FREE: [
        QuotaLimit(QuotaMetric.STORAGE_BYTES, 1_073_741_824, QuotaPolicy.HARD),
        QuotaLimit(QuotaMetric.SEATS, 3, QuotaPolicy.HARD),
        QuotaLimit(QuotaMetric.DOCUMENTS, 500, QuotaPolicy.HARD),
    ],
    PlanTier.STARTER: [
        QuotaLimit(QuotaMetric.STORAGE_BYTES, 10_737_418_240, QuotaPolicy.SOFT),
        QuotaLimit(QuotaMetric.SEATS, 10, QuotaPolicy.HARD),
        QuotaLimit(QuotaMetric.DOCUMENTS, 5_000, QuotaPolicy.SOFT),
    ],
    PlanTier.PROFESSIONAL: [
        QuotaLimit(QuotaMetric.STORAGE_BYTES, 107_374_182_400, QuotaPolicy.OVERAGE_BILLING, 5),
        QuotaLimit(QuotaMetric.SEATS, 50, QuotaPolicy.HARD),
        QuotaLimit(QuotaMetric.DOCUMENTS, 50_000, QuotaPolicy.SOFT),
    ],
    PlanTier.ENTERPRISE: [
        QuotaLimit(QuotaMetric.STORAGE_BYTES, 1_099_511_627_776, QuotaPolicy.OVERAGE_BILLING, 2),
        QuotaLimit(QuotaMetric.SEATS, 500, QuotaPolicy.HARD),
        QuotaLimit(QuotaMetric.DOCUMENTS, 1_000_000, QuotaPolicy.SOFT),
    ],
}
