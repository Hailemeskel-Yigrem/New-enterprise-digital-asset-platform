"""Global search API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.analytics.global_search_service import GlobalSearchService
from vaultforge.application.analytics.schemas import GlobalSearchRequest, GlobalSearchResponse
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(
    prefix="/organizations/{organization_id}/search",
    tags=["search"],
)


async def get_global_search_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[GlobalSearchService]:
    yield GlobalSearchService(session)


@router.post("", response_model=GlobalSearchResponse)
async def global_search(
    organization_id: uuid.UUID,
    payload: GlobalSearchRequest,
    service: GlobalSearchService = Depends(get_global_search_service),
) -> GlobalSearchResponse:
    return await service.search(organization_id, payload)
