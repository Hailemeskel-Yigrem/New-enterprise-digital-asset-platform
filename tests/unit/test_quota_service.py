"""Unit tests for quota enforcement service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.billing.quota_service import QuotaService
from vaultforge.domain.billing.enums import PlanTier, QuotaMetric
from vaultforge.infrastructure.events.event_bus import InMemoryEventBus


@pytest.fixture
def service() -> QuotaService:
    plan_repo = AsyncMock()
    plan_repo.get_for_organization = AsyncMock(return_value=None)
    plan_repo.upsert = AsyncMock(side_effect=lambda p: p)
    alloc_repo = AsyncMock()
    alloc_repo.get = AsyncMock(return_value=None)
    alloc_repo.upsert = AsyncMock(side_effect=lambda a: a)
    alloc_repo.list_for_organization = AsyncMock(return_value=[])
    return QuotaService(plan_repo, alloc_repo, AsyncMock(), InMemoryEventBus())


@pytest.mark.asyncio
async def test_ensure_plan(service: QuotaService) -> None:
    org_id = uuid.uuid4()
    plan = await service.ensure_plan(org_id, PlanTier.FREE)
    assert plan.tier == PlanTier.FREE


@pytest.mark.asyncio
async def test_check_quota_allowed(service: QuotaService) -> None:
    org_id = uuid.uuid4()
    result = await service.check_quota(org_id, QuotaMetric.STORAGE_BYTES, 100)
    assert result.allowed is True


@pytest.mark.asyncio
async def test_list_quota_status(service: QuotaService) -> None:
    org_id = uuid.uuid4()
    statuses = await service.list_quota_status(org_id)
    assert isinstance(statuses, list)
