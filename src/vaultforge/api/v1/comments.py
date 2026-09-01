"""Comment API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.collaboration.comment_service import CommentService
from vaultforge.application.collaboration.notification_service import NotificationService
from vaultforge.application.collaboration.schemas import (
    CommentCreateRequest,
    CommentResponse,
    CommentUpdateRequest,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.collaboration_repository import (
    SqlAlchemyCommentRepository,
    SqlAlchemyMentionRepository,
    SqlAlchemyNotificationRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/comments", tags=["comments"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


async def get_comment_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[CommentService]:
    notification_service = NotificationService(SqlAlchemyNotificationRepository(session))
    yield CommentService(
        SqlAlchemyCommentRepository(session),
        SqlAlchemyMentionRepository(session),
        notification_service,
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


@router.post("", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    organization_id: uuid.UUID,
    payload: CommentCreateRequest,
    service: CommentService = Depends(get_comment_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> CommentResponse:
    try:
        return await service.create_comment(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/{resource_type}/{resource_id}", response_model=list[CommentResponse])
async def list_comments(
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    service: CommentService = Depends(get_comment_service),
) -> list[CommentResponse]:
    try:
        return await service.list_comments(organization_id, resource_type, resource_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.patch("/{comment_id}", response_model=CommentResponse)
async def update_comment(
    organization_id: uuid.UUID,
    comment_id: uuid.UUID,
    payload: CommentUpdateRequest,
    service: CommentService = Depends(get_comment_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> CommentResponse:
    try:
        return await service.update_comment(
            organization_id,
            comment_id,
            _resolve_user_id(x_user_id),
            payload,
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/{comment_id}", response_model=CommentResponse)
async def delete_comment(
    organization_id: uuid.UUID,
    comment_id: uuid.UUID,
    service: CommentService = Depends(get_comment_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> CommentResponse:
    try:
        return await service.delete_comment(
            organization_id, comment_id, _resolve_user_id(x_user_id)
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
