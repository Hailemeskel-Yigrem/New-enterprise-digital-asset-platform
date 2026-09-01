"""Folder API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.assets.folder_service import FolderService
from vaultforge.application.assets.schemas import (
    FolderCreateRequest,
    FolderMoveRequest,
    FolderRenameRequest,
    FolderResponse,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.folder_repository import (
    SqlAlchemyFolderRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/folders", tags=["folders"])


async def get_folder_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[FolderService]:
    yield FolderService(SqlAlchemyFolderRepository(session))


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    organization_id: uuid.UUID,
    payload: FolderCreateRequest,
    service: FolderService = Depends(get_folder_service),
) -> FolderResponse:
    try:
        return await service.create_folder(organization_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("", response_model=list[FolderResponse])
async def list_folders(
    organization_id: uuid.UUID,
    parent_id: uuid.UUID | None = None,
    service: FolderService = Depends(get_folder_service),
) -> list[FolderResponse]:
    return await service.list_folders(organization_id, parent_id=parent_id)


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    organization_id: uuid.UUID,
    folder_id: uuid.UUID,
    service: FolderService = Depends(get_folder_service),
) -> FolderResponse:
    try:
        return await service.get_folder(organization_id, folder_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.patch("/{folder_id}/rename", response_model=FolderResponse)
async def rename_folder(
    organization_id: uuid.UUID,
    folder_id: uuid.UUID,
    payload: FolderRenameRequest,
    service: FolderService = Depends(get_folder_service),
) -> FolderResponse:
    try:
        return await service.rename_folder(organization_id, folder_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.patch("/{folder_id}/move", response_model=FolderResponse)
async def move_folder(
    organization_id: uuid.UUID,
    folder_id: uuid.UUID,
    payload: FolderMoveRequest,
    service: FolderService = Depends(get_folder_service),
) -> FolderResponse:
    try:
        return await service.move_folder(organization_id, folder_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


def _http_error(exc: VaultForgeError) -> Exception:
    from fastapi import HTTPException

    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
    }.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})
