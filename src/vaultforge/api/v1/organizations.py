"""Organization API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from vaultforge.api.deps import CurrentUser, OrganizationServiceDep, _raise_http
from vaultforge.application.identity.schemas import (
    InviteMemberRequest,
    MembershipResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from vaultforge.core.exceptions import VaultForgeError

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    payload: OrganizationCreate,
    current_user: CurrentUser,
    org_service: OrganizationServiceDep,
) -> OrganizationResponse:
    try:
        return await org_service.create_organization(payload, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    current_user: CurrentUser,
    org_service: OrganizationServiceDep,
) -> list[OrganizationResponse]:
    try:
        return await org_service.list_for_user(current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    org_service: OrganizationServiceDep,
) -> OrganizationResponse:
    try:
        return await org_service.get_organization(org_id, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    payload: OrganizationUpdate,
    current_user: CurrentUser,
    org_service: OrganizationServiceDep,
) -> OrganizationResponse:
    try:
        return await org_service.update_organization(org_id, payload, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.post("/{org_id}/members/invite", response_model=MembershipResponse, status_code=201)
async def invite_member(
    org_id: uuid.UUID,
    payload: InviteMemberRequest,
    current_user: CurrentUser,
    org_service: OrganizationServiceDep,
) -> MembershipResponse:
    try:
        return await org_service.invite_member(org_id, payload, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.get("/{org_id}/members", response_model=list[MembershipResponse])
async def list_members(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    org_service: OrganizationServiceDep,
) -> list[MembershipResponse]:
    try:
        return await org_service.list_members(org_id, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")
