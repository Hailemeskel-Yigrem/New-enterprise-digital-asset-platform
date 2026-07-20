"""Compliance domain entities."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import Entity, utc_now
from vaultforge.domain.compliance.enums import (
    ClassificationLevel,
    ComplianceHoldStatus,
    DataSubjectRequestStatus,
    DataSubjectRequestType,
    ExportFormat,
    ExportStatus,
)

_LEVEL_ORDER = {
    ClassificationLevel.PUBLIC: 0,
    ClassificationLevel.INTERNAL: 1,
    ClassificationLevel.CONFIDENTIAL: 2,
    ClassificationLevel.RESTRICTED: 3,
    ClassificationLevel.TOP_SECRET: 4,
}


@dataclass(slots=True)
class ClassificationLabel(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    level: ClassificationLevel = ClassificationLevel.INTERNAL
    color: str = "#64748b"
    description: str = ""
    is_default: bool = False
    requires_justification: bool = False
    auto_apply_rules: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValidationError("Classification label name is required")

    def dominates(self, other: ClassificationLabel) -> bool:
        return _LEVEL_ORDER[self.level] >= _LEVEL_ORDER[other.level]


@dataclass(slots=True)
class ClassificationPolicy(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: str = ""
    default_label_id: uuid.UUID | None = None
    enforce_on_upload: bool = True
    block_downgrade: bool = True
    allowed_transitions: dict[str, list[str]] = field(default_factory=dict)
    is_active: bool = True

    def is_transition_allowed(
        self, from_level: ClassificationLevel, to_level: ClassificationLevel
    ) -> bool:
        if from_level == to_level:
            return True
        if self.block_downgrade and _LEVEL_ORDER[to_level] < _LEVEL_ORDER[from_level]:
            return False
        allowed = self.allowed_transitions.get(from_level.value, [])
        return not allowed or to_level.value in allowed


@dataclass(slots=True)
class ComplianceHold(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    matter_id: str = ""
    description: str = ""
    status: ComplianceHoldStatus = ComplianceHoldStatus.ACTIVE
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    released_by: uuid.UUID | None = None
    released_at: datetime | None = None
    resource_ids: list[uuid.UUID] = field(default_factory=list)
    folder_ids: list[uuid.UUID] = field(default_factory=list)
    custodian_ids: list[uuid.UUID] = field(default_factory=list)

    def is_active(self) -> bool:
        return self.status == ComplianceHoldStatus.ACTIVE

    def covers_resource(self, resource_id: uuid.UUID, folder_id: uuid.UUID | None = None) -> bool:
        if not self.is_active():
            return False
        if resource_id in self.resource_ids:
            return True
        return folder_id is not None and folder_id in self.folder_ids

    def release(self, actor_id: uuid.UUID) -> None:
        self.status = ComplianceHoldStatus.RELEASED
        self.released_by = actor_id
        self.released_at = utc_now()
        self.touch()


@dataclass(slots=True)
class ExportManifest(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    hold_id: uuid.UUID = field(default_factory=uuid.uuid4)
    entries: list[dict[str, str]] = field(default_factory=list)
    checksum_sha256: str = ""

    def add_entry(
        self, resource_id: uuid.UUID, filename: str, size_bytes: int, storage_key: str
    ) -> None:
        self.entries.append(
            {
                "resource_id": str(resource_id),
                "filename": filename,
                "size_bytes": str(size_bytes),
                "storage_key": storage_key,
            }
        )
        self.touch()

    def finalize(self) -> str:
        payload = json.dumps(self.entries, sort_keys=True)
        self.checksum_sha256 = hashlib.sha256(payload.encode()).hexdigest()
        self.touch()
        return self.checksum_sha256


@dataclass(slots=True)
class ExportPackage(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    hold_id: uuid.UUID = field(default_factory=uuid.uuid4)
    manifest_id: uuid.UUID = field(default_factory=uuid.uuid4)
    format: ExportFormat = ExportFormat.ZIP
    status: ExportStatus = ExportStatus.PENDING
    storage_key: str = ""
    requested_by: uuid.UUID = field(default_factory=uuid.uuid4)
    error_message: str = ""

    def mark_processing(self) -> None:
        self.status = ExportStatus.PROCESSING
        self.touch()

    def mark_completed(self, storage_key: str) -> None:
        self.status = ExportStatus.COMPLETED
        self.storage_key = storage_key
        self.touch()

    def mark_failed(self, message: str) -> None:
        self.status = ExportStatus.FAILED
        self.error_message = message[:2000]
        self.touch()


@dataclass(slots=True)
class ComplianceHoldExport(Entity):
    hold: ComplianceHold = field(default_factory=ComplianceHold)
    manifest: ExportManifest = field(default_factory=ExportManifest)
    package: ExportPackage = field(default_factory=ExportPackage)


@dataclass(slots=True)
class DataSubjectRequest(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    subject_email: str = ""
    request_type: DataSubjectRequestType = DataSubjectRequestType.ACCESS
    status: DataSubjectRequestStatus = DataSubjectRequestStatus.OPEN
    due_at: datetime = field(default_factory=lambda: utc_now() + timedelta(days=30))

    def fulfill(self) -> None:
        self.status = DataSubjectRequestStatus.FULFILLED
        self.touch()
