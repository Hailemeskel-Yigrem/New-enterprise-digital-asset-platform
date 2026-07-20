"""Compliance hold creation and export packaging service."""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from dataclasses import dataclass

from vaultforge.application.compliance.schemas import (
    ComplianceHoldCreateRequest,
    ComplianceHoldResponse,
    ExportPackageRequest,
    ExportPackageResponse,
)
from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.domain.compliance.entities import ComplianceHold, ExportManifest, ExportPackage
from vaultforge.domain.compliance.repositories import (
    ComplianceHoldRepository,
    ExportManifestRepository,
    ExportPackageRepository,
    HoldQuery,
)
from vaultforge.infrastructure.storage.base import StorageBackend


@dataclass(frozen=True, slots=True)
class ExportResourceDescriptor:
    resource_id: uuid.UUID
    filename: str
    storage_key: str
    size_bytes: int
    content_type: str = "application/octet-stream"


@dataclass(slots=True)
class HoldExportService:
    holds: ComplianceHoldRepository
    manifests: ExportManifestRepository
    packages: ExportPackageRepository
    storage: StorageBackend

    async def create_hold(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ComplianceHoldCreateRequest,
    ) -> ComplianceHoldResponse:
        hold = ComplianceHold(
            organization_id=organization_id,
            name=payload.name,
            matter_id=payload.matter_id,
            description=payload.description,
            created_by=actor_id,
            resource_ids=list(payload.resource_ids),
            folder_ids=list(payload.folder_ids),
        )
        saved = await self.holds.add(hold)
        return ComplianceHoldResponse.model_validate(saved)

    async def release_hold(
        self,
        organization_id: uuid.UUID,
        hold_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> ComplianceHoldResponse:
        hold = await self._require_hold(organization_id, hold_id)
        hold.release(actor_id)
        saved = await self.holds.update(hold)
        return ComplianceHoldResponse.model_validate(saved)

    async def list_holds(self, organization_id: uuid.UUID) -> list[ComplianceHoldResponse]:
        holds = await self.holds.list(HoldQuery(organization_id=organization_id))
        return [ComplianceHoldResponse.model_validate(h) for h in holds]

    async def request_export(
        self,
        organization_id: uuid.UUID,
        hold_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ExportPackageRequest,
        resources: list[ExportResourceDescriptor],
    ) -> ExportPackageResponse:
        hold = await self._require_hold(organization_id, hold_id)
        if not hold.is_active():
            raise ValidationError("Cannot export inactive hold")
        manifest = ExportManifest(organization_id=organization_id, hold_id=hold.id)
        for resource in resources:
            manifest.add_entry(
                resource.resource_id,
                resource.filename,
                resource.size_bytes,
                resource.storage_key,
            )
        manifest.finalize()
        saved_manifest = await self.manifests.add(manifest)
        package = ExportPackage(
            organization_id=organization_id,
            hold_id=hold.id,
            manifest_id=saved_manifest.id,
            format=payload.format,
            requested_by=actor_id,
        )
        saved_package = await self.packages.add(package)
        try:
            storage_key = await self._build_export_package(
                saved_package, saved_manifest, resources, payload
            )
            saved_package.mark_completed(storage_key)
        except Exception as exc:
            saved_package.mark_failed(str(exc))
        saved_package = await self.packages.update(saved_package)
        return ExportPackageResponse.model_validate(saved_package)

    async def _build_export_package(
        self,
        package: ExportPackage,
        manifest: ExportManifest,
        resources: list[ExportResourceDescriptor],
        payload: ExportPackageRequest,
    ) -> str:
        package.mark_processing()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for resource in resources:
                data = await self.storage.get(resource.storage_key)
                archive.writestr(resource.filename, data)
            archive.writestr("manifest.json", json.dumps(manifest.entries, indent=2))
            if payload.include_metadata:
                archive.writestr("metadata.json", json.dumps({"hold_id": str(package.hold_id)}))
        storage_key = f"exports/{package.organization_id}/{package.id}.zip"
        await self.storage.put(storage_key, buffer.getvalue(), content_type="application/zip")
        return storage_key

    async def _require_hold(self, organization_id: uuid.UUID, hold_id: uuid.UUID) -> ComplianceHold:
        hold = await self.holds.get_by_id(organization_id, hold_id)
        if hold is None:
            raise NotFoundError("Compliance hold not found")
        return hold
