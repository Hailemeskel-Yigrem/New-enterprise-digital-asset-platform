"""Unit tests for bulk asset operations."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.assets.bulk_operations import (
    BulkDeleteOptions,
    BulkMoveOptions,
    BulkOperationItem,
    BulkOperationsService,
    BulkRetagOptions,
)
from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.assets.entities import Document


@pytest.fixture
def doc_repo() -> AsyncMock:
    repo = AsyncMock()
    doc = Document(name="Test Doc", tags=["alpha"])
    repo.get_by_id = AsyncMock(return_value=doc)
    repo.update = AsyncMock(side_effect=lambda d: d)
    repo.hard_delete = AsyncMock()
    return repo


@pytest.fixture
def service(doc_repo: AsyncMock) -> BulkOperationsService:
    return BulkOperationsService(
        documents=doc_repo,
        folders=AsyncMock(get_by_id=AsyncMock(return_value=object())),
        metadata_values=AsyncMock(),
        holds=AsyncMock(list_active_for_resource=AsyncMock(return_value=[])),
    )


@pytest.mark.asyncio
async def test_move_dry_run(service: BulkOperationsService, doc_repo: AsyncMock) -> None:
    org_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    result = await service.move_documents(
        org_id,
        uuid.uuid4(),
        [BulkOperationItem(resource_id=doc_id)],
        BulkMoveOptions(target_folder_id=None, dry_run=True),
    )
    assert result.succeeded == 1
    doc_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_soft(service: BulkOperationsService, doc_repo: AsyncMock) -> None:
    org_id = uuid.uuid4()
    result = await service.delete_documents(
        org_id,
        uuid.uuid4(),
        [BulkOperationItem(resource_id=uuid.uuid4())],
        BulkDeleteOptions(permanent=False),
    )
    assert result.succeeded == 1
    doc_repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_retag_add_tags(service: BulkOperationsService) -> None:
    org_id = uuid.uuid4()
    result = await service.retag_documents(
        org_id,
        uuid.uuid4(),
        [BulkOperationItem(resource_id=uuid.uuid4())],
        BulkRetagOptions(add_tags=frozenset({"beta"})),
    )
    assert result.succeeded == 1


@pytest.mark.asyncio
async def test_move_missing_folder(service: BulkOperationsService) -> None:
    service.folders.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await service.move_documents(
            uuid.uuid4(),
            uuid.uuid4(),
            [BulkOperationItem(resource_id=uuid.uuid4())],
            BulkMoveOptions(target_folder_id=uuid.uuid4()),
        )
