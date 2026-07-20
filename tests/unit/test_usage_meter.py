"""Unit tests for usage metering service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.billing.usage_meter import UsageMeter


@pytest.fixture
def snapshot_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_current = AsyncMock(return_value=None)
    repo.upsert = AsyncMock(side_effect=lambda s: s)
    return repo


@pytest.fixture
def meter(snapshot_repo: AsyncMock) -> UsageMeter:
    return UsageMeter(AsyncMock(append=AsyncMock()), snapshot_repo)


@pytest.mark.asyncio
async def test_record_storage_delta(meter: UsageMeter, snapshot_repo: AsyncMock) -> None:
    org_id = uuid.uuid4()
    result = await meter.record_storage_delta(org_id, 2048)
    assert result.organization_id == org_id
    snapshot_repo.upsert.assert_awaited()


@pytest.mark.asyncio
async def test_assign_seat(meter: UsageMeter) -> None:
    org_id = uuid.uuid4()
    result = await meter.assign_seat(org_id)
    assert result.totals.get("seats") == 1


@pytest.mark.asyncio
async def test_release_seat(meter: UsageMeter) -> None:
    org_id = uuid.uuid4()
    await meter.assign_seat(org_id)
    await meter.assign_seat(org_id)
    result = await meter.release_seat(org_id)
    assert result.totals.get("seats") == 1
