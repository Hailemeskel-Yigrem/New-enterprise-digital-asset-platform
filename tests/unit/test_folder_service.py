"""Unit tests for FolderService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.assets.folder_service import FolderService
from vaultforge.application.assets.schemas import (
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRenameRequest,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError
from vaultforge.domain.assets.entities import Folder
from vaultforge.domain.assets.enums import FolderKind


def _now() -> datetime:
    return datetime.now(UTC)


def _folder(**overrides: object) -> Folder:
    folder = Folder(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Contracts",
        kind=FolderKind.STANDARD,
        description="",
        created_at=_now(),
        updated_at=_now(),
    )
    for key, value in overrides.items():
        setattr(folder, key, value)
    return folder


@pytest.fixture
def repo() -> AsyncMock:
    mock = AsyncMock()
    mock.add = AsyncMock(side_effect=lambda folder: folder)
    mock.update = AsyncMock(side_effect=lambda folder: folder)
    mock.get_by_name_and_parent = AsyncMock(return_value=None)
    mock.list_descendant_ids = AsyncMock(return_value=[])
    mock.list_children = AsyncMock(return_value=[])
    return mock


@pytest.mark.asyncio
async def test_create_folder_persists(repo: AsyncMock) -> None:
    service = FolderService(repo)
    org_id = uuid.uuid4()
    response = await service.create_folder(
        org_id,
        FolderCreateRequest(name=" Legal ", description=" docs "),
    )
    assert response.name == "Legal"
    assert response.description == "docs"
    repo.add.assert_awaited()


@pytest.mark.asyncio
async def test_create_folder_requires_parent(repo: AsyncMock) -> None:
    repo.get_by_id = AsyncMock(return_value=None)
    service = FolderService(repo)
    with pytest.raises(NotFoundError, match="Parent folder"):
        await service.create_folder(
            uuid.uuid4(),
            FolderCreateRequest(name="Child", parent_id=uuid.uuid4()),
        )


@pytest.mark.asyncio
async def test_create_folder_rejects_duplicate_name(repo: AsyncMock) -> None:
    repo.get_by_name_and_parent = AsyncMock(return_value=_folder())
    service = FolderService(repo)
    with pytest.raises(ConflictError, match="already exists"):
        await service.create_folder(uuid.uuid4(), FolderCreateRequest(name="Contracts"))


@pytest.mark.asyncio
async def test_rename_folder_success(repo: AsyncMock) -> None:
    folder = _folder(name="Old")
    repo.get_by_id = AsyncMock(return_value=folder)
    service = FolderService(repo)
    response = await service.rename_folder(
        folder.organization_id, folder.id, FolderRenameRequest(name="New")
    )
    assert response.name == "New"


@pytest.mark.asyncio
async def test_rename_folder_conflict(repo: AsyncMock) -> None:
    folder = _folder(name="Old")
    other = _folder(name="Taken", organization_id=folder.organization_id)
    repo.get_by_id = AsyncMock(return_value=folder)
    repo.get_by_name_and_parent = AsyncMock(return_value=other)
    service = FolderService(repo)
    with pytest.raises(ConflictError):
        await service.rename_folder(
            folder.organization_id, folder.id, FolderRenameRequest(name="Taken")
        )


@pytest.mark.asyncio
async def test_move_folder_requires_parent(repo: AsyncMock) -> None:
    folder = _folder()
    repo.get_by_id = AsyncMock(side_effect=[folder, None])
    service = FolderService(repo)
    with pytest.raises(NotFoundError, match="Target parent"):
        await service.move_folder(
            folder.organization_id,
            folder.id,
            FolderMoveRequest(parent_id=uuid.uuid4()),
        )


@pytest.mark.asyncio
async def test_move_folder_success(repo: AsyncMock) -> None:
    folder = _folder()
    parent = _folder(organization_id=folder.organization_id)
    repo.get_by_id = AsyncMock(side_effect=[folder, parent])
    service = FolderService(repo)
    response = await service.move_folder(
        folder.organization_id,
        folder.id,
        FolderMoveRequest(parent_id=parent.id),
    )
    assert response.parent_id == parent.id


@pytest.mark.asyncio
async def test_list_and_get_folder(repo: AsyncMock) -> None:
    folder = _folder()
    repo.list_children = AsyncMock(return_value=[folder])
    repo.get_by_id = AsyncMock(return_value=folder)
    service = FolderService(repo)
    listed = await service.list_folders(folder.organization_id)
    assert len(listed) == 1
    fetched = await service.get_folder(folder.organization_id, folder.id)
    assert fetched.id == folder.id


@pytest.mark.asyncio
async def test_get_folder_missing(repo: AsyncMock) -> None:
    repo.get_by_id = AsyncMock(return_value=None)
    service = FolderService(repo)
    with pytest.raises(NotFoundError):
        await service.get_folder(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_would_create_cycle_detects_descendant(repo: AsyncMock) -> None:
    folder_id = uuid.uuid4()
    child_id = uuid.uuid4()
    org_id = uuid.uuid4()
    child = _folder(id=child_id, organization_id=org_id, parent_id=folder_id)
    repo.get_by_id = AsyncMock(return_value=child)
    service = FolderService(repo)
    assert await service._would_create_cycle(folder_id, child_id, org_id) is True


@pytest.mark.asyncio
async def test_would_create_cycle_allows_unrelated(repo: AsyncMock) -> None:
    folder_id = uuid.uuid4()
    other = _folder(parent_id=None)
    repo.get_by_id = AsyncMock(return_value=other)
    service = FolderService(repo)
    assert await service._would_create_cycle(folder_id, other.id, other.organization_id) is False
