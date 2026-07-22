"""Folder and document aggregates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from vaultforge.core.exceptions import ConflictError, ValidationError
from vaultforge.domain.assets.enums import (
    DocumentStatus,
    FolderKind,
    SensitivityLabel,
    VersionStatus,
)
from vaultforge.domain.common import Entity, utc_now


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty")
    return cleaned


@dataclass(slots=True)
class Folder(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    parent_id: uuid.UUID | None = None
    kind: FolderKind = FolderKind.STANDARD
    description: str = ""

    def rename(self, new_name: str) -> None:
        self.name = _require_non_empty(new_name, "Folder name")
        self.touch()

    def move(
        self, new_parent_id: uuid.UUID | None, *, descendant_ids: frozenset[uuid.UUID]
    ) -> None:
        if new_parent_id == self.id:
            raise ValidationError("A folder cannot be moved into itself")
        if new_parent_id is not None and new_parent_id in descendant_ids:
            raise ValidationError("A folder cannot be moved into one of its descendants")
        self.parent_id = new_parent_id
        self.touch()


@dataclass(slots=True)
class DocumentVersion(Entity):
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    version_number: int = 1
    storage_key: str = ""
    checksum_sha256: str = ""
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    status: VersionStatus = VersionStatus.CURRENT
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    comment: str = ""

    def mark_superseded(self) -> None:
        self.status = VersionStatus.SUPERSEDED
        self.touch()

    def mark_current(self) -> None:
        self.status = VersionStatus.CURRENT
        self.touch()


@dataclass(slots=True)
class DocumentLock(Entity):
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    locked_by: uuid.UUID = field(default_factory=uuid.uuid4)
    locked_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None

    def is_active(self, *, now: datetime | None = None) -> bool:
        reference = now or utc_now()
        return not (self.expires_at is not None and reference >= self.expires_at)


@dataclass(slots=True)
class Document(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    folder_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    status: DocumentStatus = DocumentStatus.DRAFT
    sensitivity: SensitivityLabel = SensitivityLabel.INTERNAL
    tags: list[str] = field(default_factory=list)
    current_version_id: uuid.UUID | None = None
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    deleted_at: datetime | None = None

    def rename(self, new_name: str) -> None:
        self._ensure_not_deleted()
        self.name = _require_non_empty(new_name, "Document name")
        self.touch()

    def set_tags(self, tags: list[str]) -> None:
        self._ensure_not_deleted()
        self.tags = sorted({tag.strip().lower() for tag in tags if tag.strip()})
        self.touch()

    def activate(self) -> None:
        self._ensure_not_deleted()
        if self.current_version_id is None:
            raise ValidationError("Document cannot be activated without a version")
        self.status = DocumentStatus.ACTIVE
        self.touch()

    def archive(self) -> None:
        self._ensure_not_deleted()
        self.status = DocumentStatus.ARCHIVED
        self.touch()

    def soft_delete(self) -> None:
        if self.status == DocumentStatus.DELETED:
            return
        self.status = DocumentStatus.DELETED
        self.deleted_at = utc_now()
        self.touch()

    def attach_version(self, version: DocumentVersion) -> None:
        self._ensure_not_deleted()
        if version.document_id != self.id:
            raise ValidationError("Version does not belong to this document")
        self.current_version_id = version.id
        if self.status == DocumentStatus.DRAFT:
            self.status = DocumentStatus.ACTIVE
        self.touch()

    def ensure_checkout_allowed(self, lock: DocumentLock | None) -> None:
        self._ensure_not_deleted()
        if lock is not None and lock.is_active():
            raise ConflictError("Document is checked out")

    def checkout(self, user_id: uuid.UUID, *, expires_at: datetime | None = None) -> DocumentLock:
        self._ensure_not_deleted()
        return DocumentLock(
            document_id=self.id,
            locked_by=user_id,
            expires_at=expires_at,
        )

    def checkin(self, lock: DocumentLock, user_id: uuid.UUID) -> None:
        self._ensure_not_deleted()
        if not lock.is_active():
            raise ConflictError("Checkout lock is no longer active")
        if lock.locked_by != user_id:
            raise ConflictError("Only the user who checked out the document may check it in")
        self.touch()

    def _ensure_not_deleted(self) -> None:
        if self.status == DocumentStatus.DELETED:
            raise ConflictError("Document has been deleted")
