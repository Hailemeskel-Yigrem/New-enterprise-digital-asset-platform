"""User profile API routes scoped to an organization."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from vaultforge.api.deps import CurrentUser, DbSession, require_permission
from vaultforge.application.identity.schemas import UserResponse
from vaultforge.core.pagination import Page, PageParams
from vaultforge.domain.identity.enums import MembershipStatus, Permission
from vaultforge.infrastructure.persistence.repositories import (
    SqlAlchemyMembershipRepository,
    SqlAlchemyUserRepository,
)

router = APIRouter(prefix="/organizations/{org_id}/users", tags=["users"])


class UserProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


async def _require_active_membership(
    org_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
) -> None:
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


@router.get("", response_model=Page[UserResponse])
async def list_org_users(
    org_id: uuid.UUID,
    db: DbSession,
    current_user: CurrentUser,
    params: PageParams = Depends(),
    _: None = Depends(_require_active_membership),
) -> Page[UserResponse]:
    memberships = await SqlAlchemyMembershipRepository(db).list_for_org(org_id)
    active = [m for m in memberships if m.status == MembershipStatus.ACTIVE]
    total = len(active)
    page_slice = active[params.offset : params.offset + params.limit]

    users_repo = SqlAlchemyUserRepository(db)
    items: list[UserResponse] = []
    for membership in page_slice:
        user = await users_repo.get_by_id(membership.user_id)
        if user is not None:
            items.append(UserResponse.model_validate(user))

    return Page.build(items, total=total, params=params)


@router.get("/me", response_model=UserResponse)
async def get_my_org_profile(
    current_user: CurrentUser,
    _: None = Depends(_require_active_membership),
) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    payload: UserProfileUpdate,
    db: DbSession,
    current_user: CurrentUser,
    _: None = Depends(_require_active_membership),
) -> UserResponse:
    users_repo = SqlAlchemyUserRepository(db)
    user = await users_repo.get_by_id(current_user.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "User not found"},
        )
    user.full_name = payload.full_name
    user.touch()
    updated = await users_repo.update(user)
    return UserResponse.model_validate(updated)


@router.get("/{user_id}", response_model=UserResponse)
async def get_org_user(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DbSession,
    _: None = Depends(_require_active_membership),
) -> UserResponse:
    membership = await SqlAlchemyMembershipRepository(db).get(org_id, user_id)
    if membership is None or membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "User not found in organization"},
        )
    user = await SqlAlchemyUserRepository(db).get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "User not found"},
        )
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.USER_MANAGE))],
)
async def update_org_user_profile(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: UserProfileUpdate,
    db: DbSession,
) -> UserResponse:
    target_membership = await SqlAlchemyMembershipRepository(db).get(org_id, user_id)
    if target_membership is None or target_membership.status != MembershipStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "User not found in organization"},
        )
    users_repo = SqlAlchemyUserRepository(db)
    user = await users_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "User not found"},
        )
    user.full_name = payload.full_name
    user.touch()
    updated = await users_repo.update(user)
    return UserResponse.model_validate(updated)
