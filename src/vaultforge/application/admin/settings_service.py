"""Organization settings get/update service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.assets.enums import SensitivityLabel
from vaultforge.infrastructure.persistence.models.settings import OrganizationSettingsModel


class OrganizationSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: uuid.UUID
    default_sensitivity: SensitivityLabel
    require_version_approval: bool
    notifications_enabled: bool
    max_upload_mb: int
    retention_days: int
    extra: dict = Field(default_factory=dict)


class OrganizationSettingsUpdate(BaseModel):
    default_sensitivity: SensitivityLabel | None = None
    require_version_approval: bool | None = None
    notifications_enabled: bool | None = None
    max_upload_mb: int | None = Field(default=None, ge=1, le=10240)
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    extra: dict | None = None


@dataclass
class SettingsRepository:
    session: AsyncSession

    async def get(self, organization_id: uuid.UUID) -> OrganizationSettingsModel | None:
        stmt = select(OrganizationSettingsModel).where(
            OrganizationSettingsModel.organization_id == organization_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, model: OrganizationSettingsModel) -> OrganizationSettingsModel:
        self.session.add(model)
        await self.session.flush()
        return model

    async def update(self, model: OrganizationSettingsModel) -> OrganizationSettingsModel:
        await self.session.flush()
        return model


class SettingsService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SettingsRepository(session)

    async def get_settings(self, organization_id: uuid.UUID) -> OrganizationSettingsResponse:
        model = await self._repo.get(organization_id)
        if model is None:
            model = await self._repo.add(
                OrganizationSettingsModel(organization_id=organization_id)
            )
        return self._to_response(model)

    async def update_settings(
        self,
        organization_id: uuid.UUID,
        payload: OrganizationSettingsUpdate,
    ) -> OrganizationSettingsResponse:
        model = await self._repo.get(organization_id)
        if model is None:
            raise NotFoundError("Organization settings not found")

        if payload.default_sensitivity is not None:
            model.default_sensitivity = payload.default_sensitivity.value
        if payload.require_version_approval is not None:
            model.require_version_approval = payload.require_version_approval
        if payload.notifications_enabled is not None:
            model.notifications_enabled = payload.notifications_enabled
        if payload.max_upload_mb is not None:
            model.max_upload_mb = payload.max_upload_mb
        if payload.retention_days is not None:
            model.retention_days = payload.retention_days
        if payload.extra is not None:
            model.extra = payload.extra

        updated = await self._repo.update(model)
        return self._to_response(updated)

    @staticmethod
    def _to_response(model: OrganizationSettingsModel) -> OrganizationSettingsResponse:
        return OrganizationSettingsResponse(
            organization_id=model.organization_id,
            default_sensitivity=SensitivityLabel(model.default_sensitivity),
            require_version_approval=model.require_version_approval,
            notifications_enabled=model.notifications_enabled,
            max_upload_mb=model.max_upload_mb,
            retention_days=model.retention_days,
            extra=dict(model.extra or {}),
        )
