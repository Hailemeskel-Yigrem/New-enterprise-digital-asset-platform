"""Usage report API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.analytics.report_service import ReportService
from vaultforge.application.analytics.schemas import UsageReportRequest, UsageReportResponse
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(
    prefix="/organizations/{organization_id}/reports",
    tags=["reports"],
)


async def get_report_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[ReportService]:
    yield ReportService(session)


@router.post("/usage", response_model=UsageReportResponse)
async def generate_usage_report(
    organization_id: uuid.UUID,
    payload: UsageReportRequest,
    service: ReportService = Depends(get_report_service),
) -> UsageReportResponse:
    return await service.generate_usage_report(organization_id, payload)
