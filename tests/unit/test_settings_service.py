"""Unit tests for organization settings service."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.admin.settings_service import (
    OrganizationSettingsUpdate,
    SettingsService,
)
from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.assets.enums import SensitivityLabel


@pytest.mark.asyncio
async def test_get_settings_creates_defaults_when_missing() -> None:
    organization_id = uuid.uuid4()
    session = AsyncMock()
    service = SettingsService(session)

    repo = service._repo
    repo.get = AsyncMock(return_value=None)
    created = SimpleNamespace(
        organization_id=organization_id,
        default_sensitivity=SensitivityLabel.INTERNAL.value,
        require_version_approval=False,
        notifications_enabled=True,
        max_upload_mb=100,
        retention_days=365,
        extra={},
    )
    repo.add = AsyncMock(return_value=created)

    response = await service.get_settings(organization_id)
    assert response.organization_id == organization_id
    assert response.default_sensitivity == SensitivityLabel.INTERNAL
    repo.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_settings_applies_changes() -> None:
    organization_id = uuid.uuid4()
    session = AsyncMock()
    service = SettingsService(session)

    model = SimpleNamespace(
        organization_id=organization_id,
        default_sensitivity=SensitivityLabel.INTERNAL.value,
        require_version_approval=False,
        notifications_enabled=True,
        max_upload_mb=100,
        retention_days=365,
        extra={},
    )
    repo = service._repo
    repo.get = AsyncMock(return_value=model)
    repo.update = AsyncMock(return_value=model)

    payload = OrganizationSettingsUpdate(
        default_sensitivity=SensitivityLabel.CONFIDENTIAL,
        require_version_approval=True,
        max_upload_mb=250,
    )
    response = await service.update_settings(organization_id, payload)

    assert response.default_sensitivity == SensitivityLabel.CONFIDENTIAL
    assert model.require_version_approval is True
    assert model.max_upload_mb == 250
    repo.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_settings_missing_raises_not_found() -> None:
    organization_id = uuid.uuid4()
    session = AsyncMock()
    service = SettingsService(session)
    service._repo.get = AsyncMock(return_value=None)

    with pytest.raises(NotFoundError):
        await service.update_settings(organization_id, OrganizationSettingsUpdate())
