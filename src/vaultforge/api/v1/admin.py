"""Administration API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.api.deps import CurrentUser, require_permission
from vaultforge.application.analytics.dashboard_service import DashboardService
from vaultforge.application.analytics.schemas import DashboardResponse
from vaultforge.domain.identity.enums import Permission
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{org_id}/admin", tags=["admin"])


async def get_dashboard_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[DashboardService]:
    yield DashboardService(session)


@router.get(
    "/overview",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission(Permission.ORG_MANAGE))],
)
async def admin_overview(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    del current_user
    return await service.get_dashboard(org_id)
