"""Export and import job API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.jobs.export_service import (
    ExportJobCreateRequest,
    ExportJobResponse,
    ExportService,
)
from vaultforge.application.jobs.import_service import (
    ImportJobCreateRequest,
    ImportJobResponse,
    ImportService,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.messaging.tasks import queue_export_job, queue_import_job
from vaultforge.infrastructure.persistence.repositories.job_repository import (
    SqlAlchemyExportJobRepository,
    SqlAlchemyImportJobRepository,
    StubDocumentExportSource,
    StubDocumentImportSink,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/jobs", tags=["jobs"])


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
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


async def get_export_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[ExportService]:
    yield ExportService(SqlAlchemyExportJobRepository(session), StubDocumentExportSource())


async def get_import_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[ImportService]:
    yield ImportService(SqlAlchemyImportJobRepository(session), StubDocumentImportSink())


@router.post("/exports", response_model=ExportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    organization_id: uuid.UUID,
    payload: ExportJobCreateRequest,
    service: ExportService = Depends(get_export_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ExportJobResponse:
    try:
        job = await service.create_export(organization_id, _resolve_user_id(x_user_id), payload)
        queue_export_job.delay(str(job.id))
        return job
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/exports", response_model=list[ExportJobResponse])
async def list_exports(
    organization_id: uuid.UUID,
    service: ExportService = Depends(get_export_service),
) -> list[ExportJobResponse]:
    return await service.list_jobs(organization_id)


@router.get("/exports/{job_id}", response_model=ExportJobResponse)
async def get_export(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    service: ExportService = Depends(get_export_service),
) -> ExportJobResponse:
    try:
        return await service.get_job(organization_id, job_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/exports/{job_id}", response_model=ExportJobResponse)
async def cancel_export(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    service: ExportService = Depends(get_export_service),
) -> ExportJobResponse:
    try:
        return await service.cancel_job(organization_id, job_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/imports", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_import(
    organization_id: uuid.UUID,
    payload: ImportJobCreateRequest,
    service: ImportService = Depends(get_import_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ImportJobResponse:
    try:
        job = await service.create_import(organization_id, _resolve_user_id(x_user_id), payload)
        queue_import_job.delay(str(job.id))
        return job
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/imports", response_model=list[ImportJobResponse])
async def list_imports(
    organization_id: uuid.UUID,
    service: ImportService = Depends(get_import_service),
) -> list[ImportJobResponse]:
    return await service.list_jobs(organization_id)


@router.get("/imports/{job_id}", response_model=ImportJobResponse)
async def get_import(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    service: ImportService = Depends(get_import_service),
) -> ImportJobResponse:
    try:
        return await service.get_job(organization_id, job_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
