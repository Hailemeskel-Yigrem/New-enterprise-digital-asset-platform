"""Billing and quota API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.billing.quota_service import QuotaService
from vaultforge.application.billing.schemas import (
    BillingPlanResponse,
    QuotaCheckRequest,
    QuotaCheckResponse,
    QuotaStatusResponse,
    UsageSnapshotResponse,
)
from vaultforge.application.billing.usage_meter import UsageMeter
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.events.event_bus import InMemoryEventBus
from vaultforge.infrastructure.persistence.repositories.in_memory_billing import (
    InMemoryBillingPlanRepository,
    InMemoryQuotaAllocationRepository,
    InMemoryUsageRecordRepository,
    InMemoryUsageSnapshotRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/billing", tags=["billing"])


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


_event_bus = InMemoryEventBus()

# NOTE: these in-memory repositories are process-local placeholders until the
# billing module gains dedicated SQLAlchemy-backed persistence. They satisfy
# the same repository protocols as the production implementations, so the
# services above can be swapped over without further changes to this router.


async def get_usage_meter(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[UsageMeter]:
    del session
    yield UsageMeter(InMemoryUsageRecordRepository(), InMemoryUsageSnapshotRepository())


async def get_quota_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[QuotaService]:
    del session
    yield QuotaService(
        InMemoryBillingPlanRepository(),
        InMemoryQuotaAllocationRepository(),
        InMemoryUsageSnapshotRepository(),
        _event_bus,
    )


@router.get("/usage", response_model=UsageSnapshotResponse)
async def get_usage(
    organization_id: uuid.UUID,
    meter: UsageMeter = Depends(get_usage_meter),
) -> UsageSnapshotResponse:
    return await meter.get_snapshot(organization_id)


@router.post("/usage/storage", response_model=UsageSnapshotResponse)
async def record_storage(
    organization_id: uuid.UUID,
    delta_bytes: int,
    meter: UsageMeter = Depends(get_usage_meter),
) -> UsageSnapshotResponse:
    return await meter.record_storage_delta(organization_id, delta_bytes)


@router.get("/quotas", response_model=list[QuotaStatusResponse])
async def list_quotas(
    organization_id: uuid.UUID,
    service: QuotaService = Depends(get_quota_service),
) -> list[QuotaStatusResponse]:
    return await service.list_quota_status(organization_id)


@router.post("/quotas/check", response_model=QuotaCheckResponse)
async def check_quota(
    organization_id: uuid.UUID,
    payload: QuotaCheckRequest,
    service: QuotaService = Depends(get_quota_service),
) -> QuotaCheckResponse:
    try:
        return await service.check_quota(organization_id, payload.metric, payload.amount)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/plan", response_model=BillingPlanResponse)
async def get_plan(
    organization_id: uuid.UUID,
    service: QuotaService = Depends(get_quota_service),
) -> BillingPlanResponse:
    plan = await service.ensure_plan(organization_id)
    return BillingPlanResponse.model_validate(plan)
