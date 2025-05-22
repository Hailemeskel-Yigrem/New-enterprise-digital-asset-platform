"""Analytics dashboard API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.analytics.dashboard_service import DashboardService
from vaultforge.application.analytics.schemas import DashboardResponse
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(
    prefix="/organizations/{organization_id}/analytics",
    tags=["analytics"],
)


async def get_dashboard_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[DashboardService]:
    yield DashboardService(session)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    organization_id: uuid.UUID,
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardResponse:
    return await service.get_dashboard(organization_id)
