"""Notification API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.collaboration.notification_service import NotificationService
from vaultforge.application.collaboration.schemas import NotificationListQuery, NotificationResponse
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.collaboration_repository import (
    SqlAlchemyNotificationRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/notifications", tags=["notifications"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


async def get_notification_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[NotificationService]:
    yield NotificationService(SqlAlchemyNotificationRepository(session))


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


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    organization_id: uuid.UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    service: NotificationService = Depends(get_notification_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> list[NotificationResponse]:
    query = NotificationListQuery(unread_only=unread_only, limit=limit, offset=offset)
    try:
        return await service.list_for_user(
            organization_id, _resolve_user_id(x_user_id), query
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    organization_id: uuid.UUID,
    notification_id: uuid.UUID,
    service: NotificationService = Depends(get_notification_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> NotificationResponse:
    try:
        return await service.mark_read(
            organization_id, notification_id, _resolve_user_id(x_user_id)
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/read-all")
async def mark_all_notifications_read(
    organization_id: uuid.UUID,
    service: NotificationService = Depends(get_notification_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> dict[str, int]:
    try:
        count = await service.mark_all_read(
            organization_id, _resolve_user_id(x_user_id)
        )
        return {"marked_read": count}
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
