"""Activity feed API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.audit.audit_service import AuditService
from vaultforge.application.audit.schemas import ActivityFeedQuery, ActivityFeedResponse
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.audit_repository import (
    SqlAlchemyActivityItemRepository,
    SqlAlchemyAuditEventRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/activity", tags=["activity"])


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


@router.post("/feed", response_model=ActivityFeedResponse)
async def query_activity_feed(
    organization_id: uuid.UUID,
    query: ActivityFeedQuery,
    service: AuditService = Depends(get_audit_service),
) -> ActivityFeedResponse:
    try:
        return await service.query_activity_feed(organization_id, query)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
