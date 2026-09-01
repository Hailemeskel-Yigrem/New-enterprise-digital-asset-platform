"""Audit API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.audit.audit_service import AuditService
from vaultforge.application.audit.schemas import (
    AuditEventCreateRequest,
    AuditEventResponse,
    AuditTimelineQuery,
    AuditTimelineResponse,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.audit_repository import (
    SqlAlchemyActivityItemRepository,
    SqlAlchemyAuditEventRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/audit", tags=["audit"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


async def get_audit_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[AuditService]:
    yield AuditService(
        SqlAlchemyAuditEventRepository(session),
        SqlAlchemyActivityItemRepository(session),
    )


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


@router.post("/events", response_model=AuditEventResponse, status_code=status.HTTP_201_CREATED)
async def record_audit_event(
    organization_id: uuid.UUID,
    payload: AuditEventCreateRequest,
    service: AuditService = Depends(get_audit_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> AuditEventResponse:
    try:
        return await service.record_event(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/timeline", response_model=AuditTimelineResponse)
async def query_audit_timeline(
    organization_id: uuid.UUID,
    query: AuditTimelineQuery,
    service: AuditService = Depends(get_audit_service),
) -> AuditTimelineResponse:
    try:
        return await service.query_timeline(organization_id, query)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
