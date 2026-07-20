"""Compliance repository interfaces."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from vaultforge.domain.compliance.entities import (
    ClassificationLabel,
    ClassificationPolicy,
    ComplianceHold,
    DataSubjectRequest,
    ExportManifest,
    ExportPackage,
)


@dataclass(frozen=True, slots=True)
class HoldQuery:
    organization_id: uuid.UUID
    status: str | None = None
    limit: int = 50
    offset: int = 0


class ClassificationLabelRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, label_id: uuid.UUID
    ) -> ClassificationLabel | None: ...
    @abstractmethod
    async def add(self, label: ClassificationLabel) -> ClassificationLabel: ...
    @abstractmethod
    async def update(self, label: ClassificationLabel) -> ClassificationLabel: ...
    @abstractmethod
    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> Sequence[ClassificationLabel]: ...


class ClassificationPolicyRepository(ABC):
    @abstractmethod
    async def get_active(self, organization_id: uuid.UUID) -> ClassificationPolicy | None: ...
    @abstractmethod
    async def upsert(self, policy: ClassificationPolicy) -> ClassificationPolicy: ...


class ComplianceHoldRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, hold_id: uuid.UUID
    ) -> ComplianceHold | None: ...
    @abstractmethod
    async def add(self, hold: ComplianceHold) -> ComplianceHold: ...
    @abstractmethod
    async def update(self, hold: ComplianceHold) -> ComplianceHold: ...
    @abstractmethod
    async def list(self, query: HoldQuery) -> Sequence[ComplianceHold]: ...
    @abstractmethod
    async def list_active_for_resource(
        self, organization_id: uuid.UUID, resource_id: uuid.UUID, folder_id: uuid.UUID | None = None
    ) -> Sequence[ComplianceHold]: ...


class ExportManifestRepository(ABC):
    @abstractmethod
    async def add(self, manifest: ExportManifest) -> ExportManifest: ...
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, manifest_id: uuid.UUID
    ) -> ExportManifest | None: ...


class ExportPackageRepository(ABC):
    @abstractmethod
    async def add(self, package: ExportPackage) -> ExportPackage: ...
    @abstractmethod
    async def update(self, package: ExportPackage) -> ExportPackage: ...
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, package_id: uuid.UUID
    ) -> ExportPackage | None: ...


class DataSubjectRequestRepository(ABC):
    @abstractmethod
    async def add(self, request: DataSubjectRequest) -> DataSubjectRequest: ...
    @abstractmethod
    async def update(self, request: DataSubjectRequest) -> DataSubjectRequest: ...
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, request_id: uuid.UUID
    ) -> DataSubjectRequest | None: ...
