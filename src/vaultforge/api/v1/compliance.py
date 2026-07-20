"""Compliance and classification API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.compliance.classification_service import (
    ClassificationService,
    ResourceClassificationStore,
)
from vaultforge.application.compliance.hold_export_service import HoldExportService
from vaultforge.application.compliance.schemas import (
    AssignClassificationRequest,
    ClassificationLabelCreateRequest,
    ClassificationLabelResponse,
    ComplianceHoldCreateRequest,
    ComplianceHoldResponse,
    ExportPackageRequest,
    ExportPackageResponse,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.compliance_repository import (
    SqlAlchemyClassificationLabelRepository,
    SqlAlchemyClassificationPolicyRepository,
    SqlAlchemyComplianceHoldRepository,
    SqlAlchemyExportManifestRepository,
    SqlAlchemyExportPackageRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage

router = APIRouter(prefix="/organizations/{organization_id}/compliance", tags=["compliance"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


def _http_error(exc: VaultForgeError) -> Exception:
    from fastapi import HTTPException

    code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "validation_error": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "forbidden": status.HTTP_403_FORBIDDEN,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


_assignments = ResourceClassificationStore()


async def get_classification_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[ClassificationService]:
    yield ClassificationService(
        SqlAlchemyClassificationLabelRepository(session),
        SqlAlchemyClassificationPolicyRepository(session),
        _assignments,
    )


async def get_hold_export_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[HoldExportService]:
    yield HoldExportService(
        SqlAlchemyComplianceHoldRepository(session),
        SqlAlchemyExportManifestRepository(session),
        SqlAlchemyExportPackageRepository(session),
        LocalFilesystemStorage("/tmp/vaultforge-exports"),
    )


@router.post(
    "/labels", response_model=ClassificationLabelResponse, status_code=status.HTTP_201_CREATED
)
async def create_label(
    organization_id: uuid.UUID,
    payload: ClassificationLabelCreateRequest,
    service: ClassificationService = Depends(get_classification_service),
) -> ClassificationLabelResponse:
    try:
        return await service.create_label(organization_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/labels", response_model=list[ClassificationLabelResponse])
async def list_labels(
    organization_id: uuid.UUID,
    service: ClassificationService = Depends(get_classification_service),
) -> list[ClassificationLabelResponse]:
    return await service.list_labels(organization_id)


@router.post("/classifications/assign", response_model=ClassificationLabelResponse)
async def assign_classification(
    organization_id: uuid.UUID,
    payload: AssignClassificationRequest,
    service: ClassificationService = Depends(get_classification_service),
) -> ClassificationLabelResponse:
    try:
        return await service.assign_classification(organization_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/holds", response_model=ComplianceHoldResponse, status_code=status.HTTP_201_CREATED)
async def create_hold(
    organization_id: uuid.UUID,
    payload: ComplianceHoldCreateRequest,
    service: HoldExportService = Depends(get_hold_export_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ComplianceHoldResponse:
    try:
        return await service.create_hold(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/holds", response_model=list[ComplianceHoldResponse])
async def list_holds(
    organization_id: uuid.UUID,
    service: HoldExportService = Depends(get_hold_export_service),
) -> list[ComplianceHoldResponse]:
    return await service.list_holds(organization_id)


@router.post("/holds/{hold_id}/release", response_model=ComplianceHoldResponse)
async def release_hold(
    organization_id: uuid.UUID,
    hold_id: uuid.UUID,
    service: HoldExportService = Depends(get_hold_export_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ComplianceHoldResponse:
    try:
        return await service.release_hold(organization_id, hold_id, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/holds/{hold_id}/exports",
    response_model=ExportPackageResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_export(
    organization_id: uuid.UUID,
    hold_id: uuid.UUID,
    payload: ExportPackageRequest,
    service: HoldExportService = Depends(get_hold_export_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ExportPackageResponse:
    try:
        return await service.request_export(
            organization_id, hold_id, _resolve_user_id(x_user_id), payload, resources=[]
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
