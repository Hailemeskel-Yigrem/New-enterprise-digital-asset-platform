"""Webhook endpoint API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.webhooks.schemas import (
    WebhookDeliveryResponse,
    WebhookEndpointCreateRequest,
    WebhookEndpointResponse,
)
from vaultforge.application.webhooks.webhook_service import WebhookService
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.webhook_repository import (
    SqlAlchemyWebhookDeliveryRepository,
    SqlAlchemyWebhookEndpointRepository,
    SqlAlchemyWebhookSubscriptionRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/webhooks", tags=["webhooks"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


def _http_error(exc: VaultForgeError) -> Exception:
    from fastapi import HTTPException

    code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "forbidden": status.HTTP_403_FORBIDDEN,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


async def get_webhook_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[WebhookService]:
    yield WebhookService(
        SqlAlchemyWebhookEndpointRepository(session),
        SqlAlchemyWebhookSubscriptionRepository(session),
        SqlAlchemyWebhookDeliveryRepository(session),
    )


@router.post(
    "/endpoints", response_model=WebhookEndpointResponse, status_code=status.HTTP_201_CREATED
)
async def create_endpoint(
    organization_id: uuid.UUID,
    payload: WebhookEndpointCreateRequest,
    service: WebhookService = Depends(get_webhook_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> WebhookEndpointResponse:
    try:
        return await service.create_endpoint(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/endpoints", response_model=list[WebhookEndpointResponse])
async def list_endpoints(
    organization_id: uuid.UUID,
    service: WebhookService = Depends(get_webhook_service),
) -> list[WebhookEndpointResponse]:
    return await service.list_endpoints(organization_id)


@router.get("/deliveries/{delivery_id}", response_model=WebhookDeliveryResponse)
async def get_delivery(
    organization_id: uuid.UUID,
    delivery_id: uuid.UUID,
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookDeliveryResponse:
    try:
        return await service.get_delivery(organization_id, delivery_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
