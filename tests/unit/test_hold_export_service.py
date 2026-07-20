"""Unit tests for hold export service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.compliance.hold_export_service import HoldExportService
from vaultforge.application.compliance.schemas import (
    ComplianceHoldCreateRequest,
    ExportPackageRequest,
)
from vaultforge.domain.compliance.entities import ComplianceHold
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage


@pytest.fixture
def hold_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock(side_effect=lambda h: h)
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock(side_effect=lambda h: h)
    repo.list = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def service(hold_repo: AsyncMock, tmp_path) -> HoldExportService:
    return HoldExportService(
        holds=hold_repo,
        manifests=AsyncMock(add=AsyncMock(side_effect=lambda m: m)),
        packages=AsyncMock(
            add=AsyncMock(side_effect=lambda p: p), update=AsyncMock(side_effect=lambda p: p)
        ),
        storage=LocalFilesystemStorage(tmp_path),
    )


@pytest.mark.asyncio
async def test_create_hold(service: HoldExportService, hold_repo: AsyncMock) -> None:
    org_id = uuid.uuid4()
    payload = ComplianceHoldCreateRequest(name="Litigation Hold", matter_id="M-001")
    result = await service.create_hold(org_id, uuid.uuid4(), payload)
    assert result.name == "Litigation Hold"
    hold_repo.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_release_hold(service: HoldExportService, hold_repo: AsyncMock) -> None:
    hold = ComplianceHold(name="H")
    hold_repo.get_by_id = AsyncMock(return_value=hold)
    result = await service.release_hold(uuid.uuid4(), hold.id, uuid.uuid4())
    assert result.status.value == "released"


@pytest.mark.asyncio
async def test_request_export_empty_resources(
    service: HoldExportService, hold_repo: AsyncMock
) -> None:
    hold = ComplianceHold(name="H")
    hold_repo.get_by_id = AsyncMock(return_value=hold)
    result = await service.request_export(
        uuid.uuid4(), hold.id, uuid.uuid4(), ExportPackageRequest(), resources=[]
    )
    assert result.hold_id == hold.id
