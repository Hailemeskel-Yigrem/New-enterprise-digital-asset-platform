"""Document preview API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.assets.preview_service import PreviewMetadata, PreviewService
from vaultforge.core.config import get_settings
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentVersionRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage

router = APIRouter(
    prefix="/organizations/{organization_id}/documents/{document_id}/previews",
    tags=["previews"],
)


def _storage() -> LocalFilesystemStorage:
    settings = get_settings()
    return LocalFilesystemStorage(settings.storage_local_path)


async def get_preview_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[PreviewService]:
    yield PreviewService(
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyDocumentVersionRepository(session),
        _storage(),
    )


def _http_error(exc: VaultForgeError) -> Exception:
    from fastapi import HTTPException, status

    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


@router.get("/metadata", response_model=PreviewMetadata)
async def preview_metadata(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: PreviewService = Depends(get_preview_service),
) -> PreviewMetadata:
    try:
        return await service.get_metadata(organization_id, document_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/thumbnail")
async def preview_thumbnail(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: PreviewService = Depends(get_preview_service),
) -> Response:
    try:
        data = await service.generate_thumbnail(organization_id, document_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
    if data is None:
        return Response(status_code=204)
    return Response(content=data, media_type="image/png")
