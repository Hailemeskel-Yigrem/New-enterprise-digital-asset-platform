"""Team API routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from vaultforge.api.deps import CurrentUser, TeamServiceDep, _raise_http
from vaultforge.application.identity.schemas import (
    TeamCreate,
    TeamMemberAddRequest,
    TeamResponse,
)
from vaultforge.core.exceptions import VaultForgeError

router = APIRouter(prefix="/organizations/{org_id}/teams", tags=["teams"])


@router.post("", response_model=TeamResponse, status_code=201)
async def create_team(
    org_id: uuid.UUID,
    payload: TeamCreate,
    current_user: CurrentUser,
    team_service: TeamServiceDep,
) -> TeamResponse:
    try:
        return await team_service.create_team(org_id, payload, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    team_service: TeamServiceDep,
) -> list[TeamResponse]:
    try:
        return await team_service.list_teams(org_id, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    org_id: uuid.UUID,
    team_id: uuid.UUID,
    current_user: CurrentUser,
    team_service: TeamServiceDep,
) -> TeamResponse:
    try:
        return await team_service.get_team(org_id, team_id, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.post("/{team_id}/members", response_model=TeamResponse)
async def add_team_member(
    org_id: uuid.UUID,
    team_id: uuid.UUID,
    payload: TeamMemberAddRequest,
    current_user: CurrentUser,
    team_service: TeamServiceDep,
) -> TeamResponse:
    try:
        return await team_service.add_member(org_id, team_id, payload, current_user.id)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")
