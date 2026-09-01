"""Document API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.assets.document_service import DocumentService
from vaultforge.application.assets.schemas import (
    CheckoutResponse,
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentUploadRequest,
    DocumentVersionCreateRequest,
)
from vaultforge.application.assets.search_service import SearchService
from vaultforge.core.config import get_settings
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.domain.assets.enums import SensitivityLabel
from vaultforge.infrastructure.persistence.repositories.document_repository import (
    SqlAlchemyDocumentLockRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentVersionRepository,
)
from vaultforge.infrastructure.persistence.repositories.folder_repository import (
    SqlAlchemyFolderRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage

router = APIRouter(prefix="/organizations/{organization_id}/documents", tags=["documents"])


def _storage() -> LocalFilesystemStorage:
    settings = get_settings()
    return LocalFilesystemStorage(settings.storage_local_path)


async def get_document_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[DocumentService]:
    storage = _storage()
    yield DocumentService(
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyDocumentVersionRepository(session),
        SqlAlchemyDocumentLockRepository(session),
        SqlAlchemyFolderRepository(session),
        storage,
    )


async def get_search_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[SearchService]:
    yield SearchService(
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyDocumentVersionRepository(session),
    )


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    organization_id: uuid.UUID,
    payload: DocumentSearchRequest,
    service: SearchService = Depends(get_search_service),
) -> DocumentSearchResponse:
    return await service.search_documents(organization_id, payload)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    organization_id: uuid.UUID,
    folder_id: uuid.UUID = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...),
    sensitivity: str = Form(default="internal"),
    tags: str = Form(default=""),
    comment: str = Form(default=""),
    service: DocumentService = Depends(get_document_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> DocumentResponse:
    content = await file.read()
    payload = DocumentUploadRequest(
        folder_id=folder_id,
        name=name,
        sensitivity=SensitivityLabel(sensitivity),
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        comment=comment,
    )
    try:
        return await service.upload_document(
            organization_id,
            _resolve_user_id(x_user_id),
            payload,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        return await service.get_document(organization_id, document_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/{document_id}/versions", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED
)
async def create_version(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    comment: str = Form(default=""),
    service: DocumentService = Depends(get_document_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> DocumentResponse:
    content = await file.read()
    payload = DocumentVersionCreateRequest(comment=comment)
    try:
        return await service.create_version(
            organization_id,
            document_id,
            _resolve_user_id(x_user_id),
            payload,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/{document_id}/checkout", response_model=CheckoutResponse)
async def checkout_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> CheckoutResponse:
    try:
        return await service.checkout(organization_id, document_id, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/{document_id}/checkin", response_model=DocumentResponse)
async def checkin_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> DocumentResponse:
    try:
        return await service.checkin(organization_id, document_id, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/{document_id}", response_model=DocumentResponse)
async def delete_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        return await service.soft_delete(organization_id, document_id)
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
