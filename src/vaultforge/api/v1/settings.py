"""Organization settings API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.api.deps import CurrentUser, _raise_http, require_permission
from vaultforge.application.admin.settings_service import (
    OrganizationSettingsResponse,
    OrganizationSettingsUpdate,
    SettingsService,
)
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.domain.identity.enums import Permission
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{org_id}/settings", tags=["settings"])


async def get_settings_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[SettingsService]:
    yield SettingsService(session)


@router.get("", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    service: SettingsService = Depends(get_settings_service),
) -> OrganizationSettingsResponse:
    del current_user
    return await service.get_settings(org_id)


@router.patch(
    "",
    response_model=OrganizationSettingsResponse,
    dependencies=[Depends(require_permission(Permission.SETTINGS_MANAGE))],
)
async def update_organization_settings(
    org_id: uuid.UUID,
    payload: OrganizationSettingsUpdate,
    current_user: CurrentUser,
    service: SettingsService = Depends(get_settings_service),
) -> OrganizationSettingsResponse:
    del current_user
    try:
        return await service.update_settings(org_id, payload)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")
