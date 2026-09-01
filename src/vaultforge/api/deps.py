"""FastAPI dependency injection helpers."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.identity.auth_service import AuthService
from vaultforge.application.identity.organization_service import OrganizationService
from vaultforge.application.identity.schemas import UserResponse
from vaultforge.application.identity.team_service import TeamService
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.domain.identity.entities import Membership
from vaultforge.domain.identity.enums import MembershipStatus, Permission
from vaultforge.infrastructure.persistence.repositories import (
    SqlAlchemyMembershipRepository,
    SqlAlchemyOrganizationRepository,
    SqlAlchemyTeamRepository,
    SqlAlchemyUserRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session
from vaultforge.infrastructure.security import TOKEN_TYPE_ACCESS, get_user_id_from_token

_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def _raise_http(exc: VaultForgeError) -> None:
    status_code = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "forbidden": status.HTTP_403_FORBIDDEN,
        "unauthorized": status.HTTP_401_UNAUTHORIZED,
        "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
    }.get(exc.code, status.HTTP_400_BAD_REQUEST)
    raise HTTPException(status_code=status_code, detail={"code": exc.code, "message": exc.message})


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(users=SqlAlchemyUserRepository(db))


def get_organization_service(db: DbSession) -> OrganizationService:
    return OrganizationService(
        organizations=SqlAlchemyOrganizationRepository(db),
        memberships=SqlAlchemyMembershipRepository(db),
        users=SqlAlchemyUserRepository(db),
    )


def get_team_service(db: DbSession) -> TeamService:
    return TeamService(
        teams=SqlAlchemyTeamRepository(db),
        memberships=SqlAlchemyMembershipRepository(db),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
TeamServiceDep = Annotated[TeamService, Depends(get_team_service)]


async def get_current_user(
    db: DbSession,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing bearer token"},
        )
    try:
        user_id = get_user_id_from_token(
            credentials.credentials,
            expected_type=TOKEN_TYPE_ACCESS,
        )
        auth_service = AuthService(users=SqlAlchemyUserRepository(db))
        return await auth_service.get_user(user_id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable") from exc


def require_permission(permission: Permission) -> Callable[..., object]:
    async def _dependency(
        org_id: uuid.UUID,
        db: DbSession,
        current_user: Annotated[UserResponse, Depends(get_current_user)],
    ) -> Membership:
        repo = SqlAlchemyMembershipRepository(db)
        membership = await repo.get(org_id, current_user.id)
        if membership is None or membership.status == MembershipStatus.REMOVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": "Not a member of this organization"},
            )
        if membership.status != MembershipStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": "Membership is not active"},
            )
        if not membership.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": "Insufficient permissions"},
            )
        return membership

    return _dependency


CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
