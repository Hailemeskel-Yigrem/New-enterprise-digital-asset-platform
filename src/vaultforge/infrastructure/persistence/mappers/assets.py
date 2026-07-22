"""Mappers between asset domain entities and persistence models."""

from __future__ import annotations

import uuid

from vaultforge.domain.assets.entities import Document, DocumentLock, DocumentVersion, Folder
from vaultforge.domain.assets.enums import (
    DocumentStatus,
    FolderKind,
    SensitivityLabel,
    VersionStatus,
)
from vaultforge.infrastructure.persistence.models.document import (
    DocumentLockModel,
    DocumentModel,
    DocumentVersionModel,
)
from vaultforge.infrastructure.persistence.models.folder import FolderModel


def folder_to_model(entity: Folder) -> FolderModel:
    return FolderModel(
        id=entity.id,
        organization_id=entity.organization_id,
        parent_id=entity.parent_id,
        name=entity.name,
        kind=entity.kind.value,
        description=entity.description,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def folder_from_model(model: FolderModel) -> Folder:
    return Folder(
        id=model.id,
        organization_id=model.organization_id,
        parent_id=model.parent_id,
        name=model.name,
        kind=FolderKind(model.kind),
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def document_to_model(entity: Document) -> DocumentModel:
    return DocumentModel(
        id=entity.id,
        organization_id=entity.organization_id,
        folder_id=entity.folder_id,
        name=entity.name,
        status=entity.status.value,
        sensitivity=entity.sensitivity.value,
        tags=list(entity.tags),
        current_version_id=entity.current_version_id,
        created_by=entity.created_by,
        deleted_at=entity.deleted_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def document_from_model(
    model: DocumentModel,
    *,
    current_version: DocumentVersion | None = None,
) -> Document:
    doc = Document(
        id=model.id,
        organization_id=model.organization_id,
        folder_id=model.folder_id,
        name=model.name,
        status=DocumentStatus(model.status),
        sensitivity=SensitivityLabel(model.sensitivity),
        tags=list(model.tags),
        current_version_id=model.current_version_id,
        created_by=model.created_by,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
    if current_version is not None:
        doc.current_version_id = current_version.id
    return doc


def document_version_to_model(entity: DocumentVersion) -> DocumentVersionModel:
    return DocumentVersionModel(
        id=entity.id,
        document_id=entity.document_id,
        version_number=entity.version_number,
        storage_key=entity.storage_key,
        checksum_sha256=entity.checksum_sha256,
        content_type=entity.content_type,
        size_bytes=entity.size_bytes,
        status=entity.status.value,
        created_by=entity.created_by,
        comment=entity.comment,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def document_version_from_model(model: DocumentVersionModel) -> DocumentVersion:
    return DocumentVersion(
        id=model.id,
        document_id=model.document_id,
        version_number=model.version_number,
        storage_key=model.storage_key,
        checksum_sha256=model.checksum_sha256,
        content_type=model.content_type,
        size_bytes=model.size_bytes,
        status=VersionStatus(model.status),
        created_by=model.created_by,
        comment=model.comment,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def document_lock_to_model(entity: DocumentLock) -> DocumentLockModel:
    return DocumentLockModel(
        id=entity.id,
        document_id=entity.document_id,
        locked_by=entity.locked_by,
        locked_at=entity.locked_at,
        expires_at=entity.expires_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def document_lock_from_model(model: DocumentLockModel) -> DocumentLock:
    return DocumentLock(
        id=model.id,
        document_id=model.document_id,
        locked_by=model.locked_by,
        locked_at=model.locked_at,
        expires_at=model.expires_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def documents_from_models(
    models: list[DocumentModel],
    *,
    versions_by_document: dict[uuid.UUID, DocumentVersion] | None = None,
) -> list[Document]:
    versions = versions_by_document or {}
    return [document_from_model(m, current_version=versions.get(m.id)) for m in models]


def folders_from_models(models: list[FolderModel]) -> list[Folder]:
    return [folder_from_model(m) for m in models]


def document_with_version_from_models(
    doc_model: DocumentModel,
    version_model: DocumentVersionModel | None,
) -> tuple[Document, DocumentVersion | None]:
    version = document_version_from_model(version_model) if version_model else None
    document = document_from_model(doc_model, current_version=version)
    return document, version


def apply_document_patch(model: DocumentModel, entity: Document) -> DocumentModel:
    model.name = entity.name
    model.status = entity.status.value
    model.sensitivity = entity.sensitivity.value
    model.tags = list(entity.tags)
    model.current_version_id = entity.current_version_id
    model.deleted_at = entity.deleted_at
    model.updated_at = entity.updated_at
    return model
