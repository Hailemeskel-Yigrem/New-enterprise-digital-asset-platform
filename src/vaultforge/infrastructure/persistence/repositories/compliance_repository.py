"""SQLAlchemy compliance repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.compliance.entities import (
    ClassificationLabel,
    ClassificationPolicy,
    ComplianceHold,
    ExportManifest,
    ExportPackage,
)
from vaultforge.domain.compliance.enums import (
    ClassificationLevel,
    ComplianceHoldStatus,
    ExportFormat,
    ExportStatus,
)
from vaultforge.domain.compliance.repositories import (
    ClassificationLabelRepository,
    ClassificationPolicyRepository,
    ComplianceHoldRepository,
    ExportManifestRepository,
    ExportPackageRepository,
    HoldQuery,
)
from vaultforge.infrastructure.persistence.models.compliance import (
    ClassificationLabelModel,
    ClassificationPolicyModel,
    ComplianceHoldModel,
    ExportManifestModel,
    ExportPackageModel,
)


class SqlAlchemyClassificationLabelRepository(ClassificationLabelRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, organization_id: uuid.UUID, label_id: uuid.UUID
    ) -> ClassificationLabel | None:
        model = await self._session.get(ClassificationLabelModel, label_id)
        if model is None or model.organization_id != organization_id:
            return None
        return ClassificationLabel(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            level=ClassificationLevel(model.level),
            color=model.color,
            description=model.description,
            is_default=model.is_default,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def add(self, label: ClassificationLabel) -> ClassificationLabel:
        model = ClassificationLabelModel(
            id=label.id,
            organization_id=label.organization_id,
            name=label.name,
            level=label.level.value,
            color=label.color,
            description=label.description,
            is_default=label.is_default,
            created_at=label.created_at,
            updated_at=label.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return label

    async def update(self, label: ClassificationLabel) -> ClassificationLabel:
        model = await self._session.get(ClassificationLabelModel, label.id)
        if model is None:
            raise ValueError("Label not found")
        model.name = label.name
        model.level = label.level.value
        model.color = label.color
        model.description = label.description
        model.is_default = label.is_default
        model.updated_at = label.updated_at
        await self._session.flush()
        return label

    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> Sequence[ClassificationLabel]:
        stmt = select(ClassificationLabelModel).where(
            ClassificationLabelModel.organization_id == organization_id
        )
        result = await self._session.execute(stmt)
        labels: list[ClassificationLabel] = []
        for model in result.scalars():
            label = await self.get_by_id(organization_id, model.id)
            if label is not None:
                labels.append(label)
        return labels


class SqlAlchemyClassificationPolicyRepository(ClassificationPolicyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, organization_id: uuid.UUID) -> ClassificationPolicy | None:
        stmt = select(ClassificationPolicyModel).where(
            ClassificationPolicyModel.organization_id == organization_id,
            ClassificationPolicyModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return ClassificationPolicy(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            description=model.description,
            default_label_id=model.default_label_id,
            enforce_on_upload=model.enforce_on_upload,
            block_downgrade=model.block_downgrade,
            allowed_transitions=dict(model.allowed_transitions_json),
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def upsert(self, policy: ClassificationPolicy) -> ClassificationPolicy:
        model = await self._session.get(ClassificationPolicyModel, policy.id)
        if model is None:
            model = ClassificationPolicyModel(
                id=policy.id,
                organization_id=policy.organization_id,
                name=policy.name,
                description=policy.description,
                default_label_id=policy.default_label_id,
                enforce_on_upload=policy.enforce_on_upload,
                block_downgrade=policy.block_downgrade,
                allowed_transitions_json=policy.allowed_transitions,
                is_active=policy.is_active,
                created_at=policy.created_at,
                updated_at=policy.updated_at,
            )
            self._session.add(model)
        else:
            model.name = policy.name
            model.description = policy.description
            model.default_label_id = policy.default_label_id
            model.enforce_on_upload = policy.enforce_on_upload
            model.block_downgrade = policy.block_downgrade
            model.allowed_transitions_json = policy.allowed_transitions
            model.is_active = policy.is_active
            model.updated_at = policy.updated_at
        await self._session.flush()
        return policy


class SqlAlchemyComplianceHoldRepository(ComplianceHoldRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ComplianceHoldModel) -> ComplianceHold:
        return ComplianceHold(
            id=model.id,
            organization_id=model.organization_id,
            name=model.name,
            matter_id=model.matter_id,
            description=model.description,
            status=ComplianceHoldStatus(model.status),
            created_by=model.created_by,
            released_by=model.released_by,
            released_at=model.released_at,
            resource_ids=list(model.resource_ids or []),
            folder_ids=list(model.folder_ids or []),
            custodian_ids=list(model.custodian_ids or []),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(
        self, organization_id: uuid.UUID, hold_id: uuid.UUID
    ) -> ComplianceHold | None:
        model = await self._session.get(ComplianceHoldModel, hold_id)
        if model is None or model.organization_id != organization_id:
            return None
        return self._to_entity(model)

    async def add(self, hold: ComplianceHold) -> ComplianceHold:
        model = ComplianceHoldModel(
            id=hold.id,
            organization_id=hold.organization_id,
            name=hold.name,
            matter_id=hold.matter_id,
            description=hold.description,
            status=hold.status.value,
            created_by=hold.created_by,
            released_by=hold.released_by,
            released_at=hold.released_at,
            resource_ids=hold.resource_ids,
            folder_ids=hold.folder_ids,
            custodian_ids=hold.custodian_ids,
            created_at=hold.created_at,
            updated_at=hold.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return hold

    async def update(self, hold: ComplianceHold) -> ComplianceHold:
        model = await self._session.get(ComplianceHoldModel, hold.id)
        if model is None:
            raise ValueError("Hold not found")
        model.status = hold.status.value
        model.released_by = hold.released_by
        model.released_at = hold.released_at
        model.resource_ids = hold.resource_ids
        model.folder_ids = hold.folder_ids
        model.updated_at = hold.updated_at
        await self._session.flush()
        return hold

    async def list(self, query: HoldQuery) -> Sequence[ComplianceHold]:
        stmt = select(ComplianceHoldModel).where(
            ComplianceHoldModel.organization_id == query.organization_id
        )
        if query.status is not None:
            stmt = stmt.where(ComplianceHoldModel.status == query.status)
        stmt = stmt.limit(query.limit).offset(query.offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars()]

    async def list_active_for_resource(
        self, organization_id: uuid.UUID, resource_id: uuid.UUID, folder_id: uuid.UUID | None = None
    ) -> Sequence[ComplianceHold]:
        holds = await self.list(
            HoldQuery(organization_id=organization_id, status="active", limit=500)
        )
        return [h for h in holds if h.covers_resource(resource_id, folder_id)]


class SqlAlchemyExportManifestRepository(ExportManifestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, manifest: ExportManifest) -> ExportManifest:
        model = ExportManifestModel(
            id=manifest.id,
            organization_id=manifest.organization_id,
            hold_id=manifest.hold_id,
            entries_json=manifest.entries,
            checksum_sha256=manifest.checksum_sha256,
            created_at=manifest.created_at,
            updated_at=manifest.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return manifest

    async def get_by_id(
        self, organization_id: uuid.UUID, manifest_id: uuid.UUID
    ) -> ExportManifest | None:
        model = await self._session.get(ExportManifestModel, manifest_id)
        if model is None or model.organization_id != organization_id:
            return None
        return ExportManifest(
            id=model.id,
            organization_id=model.organization_id,
            hold_id=model.hold_id,
            entries=list(model.entries_json),
            checksum_sha256=model.checksum_sha256,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SqlAlchemyExportPackageRepository(ExportPackageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, package: ExportPackage) -> ExportPackage:
        model = ExportPackageModel(
            id=package.id,
            organization_id=package.organization_id,
            hold_id=package.hold_id,
            manifest_id=package.manifest_id,
            format=package.format.value,
            status=package.status.value,
            storage_key=package.storage_key,
            requested_by=package.requested_by,
            error_message=package.error_message,
            created_at=package.created_at,
            updated_at=package.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return package

    async def update(self, package: ExportPackage) -> ExportPackage:
        model = await self._session.get(ExportPackageModel, package.id)
        if model is None:
            raise ValueError("Package not found")
        model.status = package.status.value
        model.storage_key = package.storage_key
        model.error_message = package.error_message
        model.updated_at = package.updated_at
        await self._session.flush()
        return package

    async def get_by_id(
        self, organization_id: uuid.UUID, package_id: uuid.UUID
    ) -> ExportPackage | None:
        model = await self._session.get(ExportPackageModel, package_id)
        if model is None or model.organization_id != organization_id:
            return None
        return ExportPackage(
            id=model.id,
            organization_id=model.organization_id,
            hold_id=model.hold_id,
            manifest_id=model.manifest_id,
            format=ExportFormat(model.format),
            status=ExportStatus(model.status),
            storage_key=model.storage_key,
            requested_by=model.requested_by,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
