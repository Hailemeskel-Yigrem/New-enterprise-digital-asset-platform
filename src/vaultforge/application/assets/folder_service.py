"""Folder management application service."""

from __future__ import annotations

import uuid

from vaultforge.application.assets.schemas import (
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRenameRequest,
    FolderResponse,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError
from vaultforge.domain.assets.entities import Folder
from vaultforge.domain.assets.repositories import FolderRepository


class FolderService:
    def __init__(self, folder_repo: FolderRepository) -> None:
        self._folders = folder_repo

    async def create_folder(
        self,
        organization_id: uuid.UUID,
        payload: FolderCreateRequest,
    ) -> FolderResponse:
        if payload.parent_id is not None:
            parent = await self._folders.get_by_id(organization_id, payload.parent_id)
            if parent is None:
                raise NotFoundError("Parent folder not found")

        existing = await self._folders.get_by_name_and_parent(
            organization_id, payload.name.strip(), payload.parent_id
        )
        if existing is not None:
            raise ConflictError("A folder with this name already exists at the target location")

        folder = Folder(
            organization_id=organization_id,
            name=payload.name.strip(),
            parent_id=payload.parent_id,
            kind=payload.kind,
            description=payload.description.strip(),
        )
        saved = await self._folders.add(folder)
        return FolderResponse.model_validate(saved)

    async def rename_folder(
        self,
        organization_id: uuid.UUID,
        folder_id: uuid.UUID,
        payload: FolderRenameRequest,
    ) -> FolderResponse:
        folder = await self._require_folder(organization_id, folder_id)
        folder.rename(payload.name)
        existing = await self._folders.get_by_name_and_parent(
            organization_id, folder.name, folder.parent_id
        )
        if existing is not None and existing.id != folder.id:
            raise ConflictError("A folder with this name already exists at the target location")
        saved = await self._folders.update(folder)
        return FolderResponse.model_validate(saved)

    async def move_folder(
        self,
        organization_id: uuid.UUID,
        folder_id: uuid.UUID,
        payload: FolderMoveRequest,
    ) -> FolderResponse:
        folder = await self._require_folder(organization_id, folder_id)
        if payload.parent_id is not None:
            parent = await self._folders.get_by_id(organization_id, payload.parent_id)
            if parent is None:
                raise NotFoundError("Target parent folder not found")

        descendants = await self._folders.list_descendant_ids(organization_id, folder.id)
        folder.move(payload.parent_id, descendant_ids=descendants)

        existing = await self._folders.get_by_name_and_parent(
            organization_id, folder.name, folder.parent_id
        )
        if existing is not None and existing.id != folder.id:
            raise ConflictError("A folder with this name already exists at the target location")

        saved = await self._folders.update(folder)
        return FolderResponse.model_validate(saved)

    async def list_folders(
        self,
        organization_id: uuid.UUID,
        *,
        parent_id: uuid.UUID | None = None,
    ) -> list[FolderResponse]:
        folders = await self._folders.list_children(organization_id, parent_id)
        return [FolderResponse.model_validate(folder) for folder in folders]

    async def get_folder(
        self,
        organization_id: uuid.UUID,
        folder_id: uuid.UUID,
    ) -> FolderResponse:
        folder = await self._require_folder(organization_id, folder_id)
        return FolderResponse.model_validate(folder)

    async def _require_folder(self, organization_id: uuid.UUID, folder_id: uuid.UUID) -> Folder:
        folder = await self._folders.get_by_id(organization_id, folder_id)
        if folder is None:
            raise NotFoundError("Folder not found")
        return folder
