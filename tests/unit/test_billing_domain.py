"""Unit tests for billing domain entities."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.billing.entities import (
    BillingPlan,
    QuotaAllocation,
    UsageSnapshot,
)
from vaultforge.domain.billing.enums import PlanTier, QuotaMetric, QuotaPolicy


def test_quota_allocation_available() -> None:
    allocation = QuotaAllocation(allocated=1000, consumed=300, reserved=100)
    assert allocation.available == 600


def test_quota_allocation_consume() -> None:
    allocation = QuotaAllocation(allocated=100, policy=QuotaPolicy.HARD)
    allocation.consume(50)
    assert allocation.consumed == 50


def test_quota_allocation_hard_limit() -> None:
    allocation = QuotaAllocation(allocated=10, policy=QuotaPolicy.HARD)
    with pytest.raises(ValidationError):
        allocation.consume(20)


def test_usage_snapshot_increment() -> None:
    snapshot = UsageSnapshot(organization_id=uuid.uuid4())
    snapshot.increment(QuotaMetric.STORAGE_BYTES, 1024)
    assert snapshot.get_total(QuotaMetric.STORAGE_BYTES) == 1024


def test_billing_plan_default_name() -> None:
    plan = BillingPlan(tier=PlanTier.FREE)
    assert plan.name == "Free"


def test_quota_allocation_refund() -> None:
    allocation = QuotaAllocation(consumed=100)
    allocation.refund(30)
    assert allocation.consumed == 70
