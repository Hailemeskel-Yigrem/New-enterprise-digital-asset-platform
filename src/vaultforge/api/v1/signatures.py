"""Digital signature API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.signatures.schemas import (
    DeclineSignatureRequest,
    SignatureRequestCreateRequest,
    SignatureRequestResponse,
    SignDocumentResponse,
)
from vaultforge.application.signatures.signature_service import SignatureService
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentVersionRepository,
)
from vaultforge.infrastructure.persistence.repositories.signature_repository import (
    SqlAlchemySignatureRequestRepository,
    SqlAlchemySignerRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/signatures", tags=["signatures"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


async def get_signature_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[SignatureService]:
    yield SignatureService(
        SqlAlchemySignatureRequestRepository(session),
        SqlAlchemySignerRepository(session),
        SqlAlchemyDocumentRepository(session),
        SqlAlchemyDocumentVersionRepository(session),
    )


def _http_error(exc: VaultForgeError) -> Exception:
    from fastapi import HTTPException

    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
    }.get(exc.code, status.HTTP_400_BAD_REQUEST)
    return HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


@router.post("", response_model=SignatureRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_signature_request(
    organization_id: uuid.UUID,
    payload: SignatureRequestCreateRequest,
    service: SignatureService = Depends(get_signature_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> SignatureRequestResponse:
    try:
        return await service.create_request(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/{request_id}", response_model=SignatureRequestResponse)
async def get_signature_request(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    service: SignatureService = Depends(get_signature_service),
) -> SignatureRequestResponse:
    try:
        return await service.get_request(organization_id, request_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/documents/{document_id}", response_model=list[SignatureRequestResponse])
async def list_document_signatures(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    service: SignatureService = Depends(get_signature_service),
) -> list[SignatureRequestResponse]:
    try:
        return await service.list_for_document(organization_id, document_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/{request_id}/sign", response_model=SignDocumentResponse)
async def sign_document(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    service: SignatureService = Depends(get_signature_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> SignDocumentResponse:
    try:
        return await service.sign(organization_id, request_id, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/{request_id}/decline", response_model=SignatureRequestResponse)
async def decline_signature(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    payload: DeclineSignatureRequest,
    service: SignatureService = Depends(get_signature_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> SignatureRequestResponse:
    try:
        return await service.decline(
            organization_id,
            request_id,
            _resolve_user_id(x_user_id),
            reason=payload.reason,
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/{request_id}/complete", response_model=SignatureRequestResponse)
async def complete_signature(
    organization_id: uuid.UUID,
    request_id: uuid.UUID,
    service: SignatureService = Depends(get_signature_service),
) -> SignatureRequestResponse:
    try:
        return await service.complete(organization_id, request_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
