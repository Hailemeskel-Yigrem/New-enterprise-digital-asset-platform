"""Retention and legal hold API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.retention.retention_service import RetentionService
from vaultforge.application.retention.schemas import (
    LegalHoldCreateRequest,
    LegalHoldResponse,
    LegalHoldUpdateRequest,
    ResourceHoldCheckResponse,
    RetentionDueQuery,
    RetentionPolicyCreateRequest,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
    RetentionScheduleResponse,
    ScheduleResourceRequest,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.share_repository import (
    SqlAlchemyLegalHoldRepository,
    SqlAlchemyRetentionPolicyRepository,
    SqlAlchemyRetentionScheduleRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/retention", tags=["retention"])


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


async def get_retention_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[RetentionService]:
    yield RetentionService(
        SqlAlchemyRetentionPolicyRepository(session),
        SqlAlchemyRetentionScheduleRepository(session),
        SqlAlchemyLegalHoldRepository(session),
    )


@router.post(
    "/policies", response_model=RetentionPolicyResponse, status_code=status.HTTP_201_CREATED
)
async def create_policy(
    organization_id: uuid.UUID,
    payload: RetentionPolicyCreateRequest,
    service: RetentionService = Depends(get_retention_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> RetentionPolicyResponse:
    try:
        return await service.create_policy(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/policies", response_model=list[RetentionPolicyResponse])
async def list_policies(
    organization_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
) -> list[RetentionPolicyResponse]:
    return await service.list_policies(organization_id)


@router.patch("/policies/{policy_id}", response_model=RetentionPolicyResponse)
async def update_policy(
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    payload: RetentionPolicyUpdateRequest,
    service: RetentionService = Depends(get_retention_service),
) -> RetentionPolicyResponse:
    try:
        return await service.update_policy(organization_id, policy_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/policies/{policy_id}", response_model=RetentionPolicyResponse)
async def disable_policy(
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
) -> RetentionPolicyResponse:
    try:
        return await service.disable_policy(organization_id, policy_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/policies/{policy_id}/schedule",
    response_model=RetentionScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def schedule_resource(
    organization_id: uuid.UUID,
    policy_id: uuid.UUID,
    payload: ScheduleResourceRequest,
    service: RetentionService = Depends(get_retention_service),
) -> RetentionScheduleResponse:
    try:
        return await service.schedule_resource(organization_id, policy_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/schedules/due", response_model=list[RetentionScheduleResponse])
async def list_due_schedules(
    organization_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
    limit: int = 100,
) -> list[RetentionScheduleResponse]:
    return await service.list_due_schedules(organization_id, RetentionDueQuery(limit=limit))


@router.post("/schedules/{schedule_id}/execute", response_model=RetentionScheduleResponse)
async def execute_schedule(
    organization_id: uuid.UUID,
    schedule_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
) -> RetentionScheduleResponse:
    try:
        return await service.execute_schedule(organization_id, schedule_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/legal-holds", response_model=LegalHoldResponse, status_code=status.HTTP_201_CREATED)
async def create_legal_hold(
    organization_id: uuid.UUID,
    payload: LegalHoldCreateRequest,
    service: RetentionService = Depends(get_retention_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> LegalHoldResponse:
    try:
        return await service.create_legal_hold(
            organization_id, _resolve_user_id(x_user_id), payload
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/legal-holds", response_model=list[LegalHoldResponse])
async def list_legal_holds(
    organization_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
) -> list[LegalHoldResponse]:
    return await service.list_legal_holds(organization_id)


@router.patch("/legal-holds/{hold_id}", response_model=LegalHoldResponse)
async def update_legal_hold(
    organization_id: uuid.UUID,
    hold_id: uuid.UUID,
    payload: LegalHoldUpdateRequest,
    service: RetentionService = Depends(get_retention_service),
) -> LegalHoldResponse:
    try:
        return await service.update_legal_hold(organization_id, hold_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/legal-holds/{hold_id}/release", response_model=LegalHoldResponse)
async def release_legal_hold(
    organization_id: uuid.UUID,
    hold_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> LegalHoldResponse:
    try:
        return await service.release_legal_hold(
            organization_id, hold_id, _resolve_user_id(x_user_id)
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/legal-holds/check/{resource_id}", response_model=ResourceHoldCheckResponse)
async def check_resource_hold(
    organization_id: uuid.UUID,
    resource_id: uuid.UUID,
    service: RetentionService = Depends(get_retention_service),
    folder_id: uuid.UUID | None = None,
) -> ResourceHoldCheckResponse:
    return await service.check_resource_hold(organization_id, resource_id, folder_id)
