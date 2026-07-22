"""Sharing and ACL API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.sharing.schemas import (
    AccessControlEntryResponse,
    ReplaceAclRequest,
    ShareAccessCheckRequest,
    ShareAccessCheckResponse,
    ShareGrantCreateRequest,
    ShareGrantResponse,
    ShareInvitationCreateRequest,
    ShareInvitationResponse,
    ShareLinkCreateRequest,
    ShareLinkResponse,
)
from vaultforge.application.sharing.share_service import ShareService
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.domain.sharing.enums import ShareResourceType
from vaultforge.infrastructure.persistence.repositories.share_repository import (
    SqlAlchemyAccessControlRepository,
    SqlAlchemyShareGrantRepository,
    SqlAlchemyShareInvitationRepository,
    SqlAlchemyShareLinkRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/shares", tags=["shares"])


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
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


async def get_share_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[ShareService]:
    yield ShareService(
        SqlAlchemyShareGrantRepository(session),
        SqlAlchemyShareLinkRepository(session),
        SqlAlchemyShareInvitationRepository(session),
        SqlAlchemyAccessControlRepository(session),
    )


@router.post("/grants", response_model=ShareGrantResponse, status_code=status.HTTP_201_CREATED)
async def create_grant(
    organization_id: uuid.UUID,
    payload: ShareGrantCreateRequest,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ShareGrantResponse:
    try:
        return await service.create_grant(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/grants/{resource_type}/{resource_id}", response_model=list[ShareGrantResponse])
async def list_grants(
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
) -> list[ShareGrantResponse]:
    try:
        return await service.list_grants(
            organization_id, ShareResourceType(resource_type), resource_id
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/grants/{grant_id}", response_model=ShareGrantResponse)
async def revoke_grant(
    organization_id: uuid.UUID,
    grant_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ShareGrantResponse:
    try:
        return await service.revoke_grant(organization_id, grant_id, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/links", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_link(
    organization_id: uuid.UUID,
    payload: ShareLinkCreateRequest,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ShareLinkResponse:
    try:
        return await service.create_link(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/links/{link_id}", response_model=ShareLinkResponse)
async def revoke_link(
    organization_id: uuid.UUID,
    link_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
) -> ShareLinkResponse:
    try:
        return await service.revoke_link(organization_id, link_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post(
    "/invitations", response_model=ShareInvitationResponse, status_code=status.HTTP_201_CREATED
)
async def create_invitation(
    organization_id: uuid.UUID,
    payload: ShareInvitationCreateRequest,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ShareInvitationResponse:
    try:
        return await service.create_invitation(
            organization_id, _resolve_user_id(x_user_id), payload
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/invitations/{token}/accept", response_model=ShareInvitationResponse)
async def accept_invitation(
    organization_id: uuid.UUID,
    token: str,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ShareInvitationResponse:
    try:
        return await service.accept_invitation(token, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.put("/acl/{resource_type}/{resource_id}", response_model=list[AccessControlEntryResponse])
async def replace_acl(
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    payload: ReplaceAclRequest,
    service: ShareService = Depends(get_share_service),
) -> list[AccessControlEntryResponse]:
    try:
        return await service.replace_acl(
            organization_id, ShareResourceType(resource_type), resource_id, payload
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/acl/{resource_type}/{resource_id}", response_model=list[AccessControlEntryResponse])
async def list_acl(
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
) -> list[AccessControlEntryResponse]:
    try:
        return await service.list_acl(
            organization_id, ShareResourceType(resource_type), resource_id
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.post("/check", response_model=ShareAccessCheckResponse)
async def check_access(
    organization_id: uuid.UUID,
    payload: ShareAccessCheckRequest,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> ShareAccessCheckResponse:
    try:
        return await service.check_access(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/with-me", response_model=list[ShareGrantResponse])
async def list_shared_with_me(
    organization_id: uuid.UUID,
    service: ShareService = Depends(get_share_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> list[ShareGrantResponse]:
    try:
        return await service.list_shared_with_user(organization_id, _resolve_user_id(x_user_id))
    except VaultForgeError as exc:
        raise _http_error(exc) from exc
