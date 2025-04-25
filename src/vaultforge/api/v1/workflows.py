"""Workflow API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.workflows.schemas import (
    StepDecisionRequest,
    StepRejectRequest,
    WorkflowDefineRequest,
    WorkflowInstanceResponse,
    WorkflowInstanceStartRequest,
    WorkflowResponse,
)
from vaultforge.application.workflows.workflow_service import WorkflowService
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.document_repository import (
    SqlAlchemyDocumentRepository,
)
from vaultforge.infrastructure.persistence.repositories.workflow_repository import (
    SqlAlchemyStepInstanceRepository,
    SqlAlchemyWorkflowInstanceRepository,
    SqlAlchemyWorkflowRepository,
    SqlAlchemyWorkflowStepRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/workflows", tags=["workflows"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


async def get_workflow_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[WorkflowService]:
    yield WorkflowService(
        SqlAlchemyWorkflowRepository(session),
        SqlAlchemyWorkflowStepRepository(session),
        SqlAlchemyWorkflowInstanceRepository(session),
        SqlAlchemyStepInstanceRepository(session),
        SqlAlchemyDocumentRepository(session),
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


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def define_workflow(
    organization_id: uuid.UUID,
    payload: WorkflowDefineRequest,
    service: WorkflowService = Depends(get_workflow_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowResponse:
    try:
        return await service.define_template(
            organization_id, _resolve_user_id(x_user_id), payload
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows(
    organization_id: uuid.UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> list[WorkflowResponse]:
    try:
        return await service.list_workflows(organization_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/instances", response_model=WorkflowInstanceResponse, status_code=status.HTTP_201_CREATED)
async def start_workflow_instance(
    organization_id: uuid.UUID,
    payload: WorkflowInstanceStartRequest,
    service: WorkflowService = Depends(get_workflow_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowInstanceResponse:
    try:
        return await service.start_instance(
            organization_id, _resolve_user_id(x_user_id), payload
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceResponse)
async def get_workflow_instance(
    organization_id: uuid.UUID,
    instance_id: uuid.UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowInstanceResponse:
    try:
        return await service.get_instance(organization_id, instance_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/instances/{instance_id}/approve", response_model=WorkflowInstanceResponse)
async def approve_workflow_step(
    organization_id: uuid.UUID,
    instance_id: uuid.UUID,
    payload: StepDecisionRequest,
    service: WorkflowService = Depends(get_workflow_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowInstanceResponse:
    try:
        return await service.approve_step(
            organization_id,
            instance_id,
            _resolve_user_id(x_user_id),
            comment=payload.comment,
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/instances/{instance_id}/reject", response_model=WorkflowInstanceResponse)
async def reject_workflow_step(
    organization_id: uuid.UUID,
    instance_id: uuid.UUID,
    payload: StepRejectRequest,
    service: WorkflowService = Depends(get_workflow_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WorkflowInstanceResponse:
    try:
        return await service.reject_step(
            organization_id,
            instance_id,
            _resolve_user_id(x_user_id),
            comment=payload.comment,
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/instances/{instance_id}/advance", response_model=WorkflowInstanceResponse)
async def advance_workflow(
    organization_id: uuid.UUID,
    instance_id: uuid.UUID,
    service: WorkflowService = Depends(get_workflow_service),
) -> WorkflowInstanceResponse:
    try:
        return await service.advance(organization_id, instance_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
