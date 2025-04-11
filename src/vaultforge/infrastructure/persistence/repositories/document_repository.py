"""SQLAlchemy document, version, and lock repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.assets.entities import Document, DocumentLock, DocumentVersion
from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel, VersionStatus
from vaultforge.domain.assets.repositories import (
    DocumentLockRepository,
    DocumentRepository,
    DocumentSearchCriteria,
    DocumentVersionRepository,
)
from vaultforge.infrastructure.persistence.models.document import (
    DocumentLockModel,
    DocumentModel,
    DocumentVersionModel,
)


def _document_to_entity(model: DocumentModel) -> Document:
    return Document(
        id=model.id,
        organization_id=model.organization_id,
        folder_id=model.folder_id,
        name=model.name,
        status=DocumentStatus(model.status),
        sensitivity=SensitivityLabel(model.sensitivity),
        tags=list(model.tags or []),
        current_version_id=model.current_version_id,
        created_by=model.created_by,
        deleted_at=model.deleted_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_document(model: DocumentModel, document: Document) -> None:
    model.organization_id = document.organization_id
    model.folder_id = document.folder_id
    model.name = document.name
    model.status = document.status.value
    model.sensitivity = document.sensitivity.value
    model.tags = list(document.tags)
    model.current_version_id = document.current_version_id
    model.created_by = document.created_by
    model.deleted_at = document.deleted_at
    model.updated_at = document.updated_at


def _version_to_entity(model: DocumentVersionModel) -> DocumentVersion:
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


def _apply_version(model: DocumentVersionModel, version: DocumentVersion) -> None:
    model.document_id = version.document_id
    model.version_number = version.version_number
    model.storage_key = version.storage_key
    model.checksum_sha256 = version.checksum_sha256
    model.content_type = version.content_type
    model.size_bytes = version.size_bytes
    model.status = version.status.value
    model.created_by = version.created_by
    model.comment = version.comment
    model.updated_at = version.updated_at


def _lock_to_entity(model: DocumentLockModel) -> DocumentLock:
    return DocumentLock(
        id=model.id,
        document_id=model.document_id,
        locked_by=model.locked_by,
        locked_at=model.locked_at,
        expires_at=model.expires_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.id == document_id,
            DocumentModel.organization_id == organization_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _document_to_entity(model) if model else None

    async def add(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            organization_id=document.organization_id,
            folder_id=document.folder_id,
            name=document.name,
            status=document.status.value,
            sensitivity=document.sensitivity.value,
            tags=list(document.tags),
            current_version_id=document.current_version_id,
            created_by=document.created_by,
            deleted_at=document.deleted_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _document_to_entity(model)

    async def update(self, document: Document) -> Document:
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            raise ValueError(f"Document {document.id} not found")
        _apply_document(model, document)
        await self._session.flush()
        return _document_to_entity(model)

    async def search(self, criteria: DocumentSearchCriteria) -> list[Document]:
        stmt: Select[tuple[DocumentModel]] = select(DocumentModel).where(
            DocumentModel.organization_id == criteria.organization_id
        )
        if not criteria.include_deleted:
            stmt = stmt.where(DocumentModel.status != DocumentStatus.DELETED.value)
        if criteria.name:
            stmt = stmt.where(DocumentModel.name.ilike(f"%{criteria.name}%"))
        if criteria.status is not None:
            stmt = stmt.where(DocumentModel.status == criteria.status.value)
        if criteria.folder_id is not None:
            stmt = stmt.where(DocumentModel.folder_id == criteria.folder_id)
        if criteria.tags:
            stmt = stmt.where(DocumentModel.tags.contains(list(criteria.tags)))
        stmt = stmt.order_by(DocumentModel.updated_at.desc()).limit(criteria.limit).offset(criteria.offset)
        result = await self._session.execute(stmt)
        return [_document_to_entity(row) for row in result.scalars().all()]


class SqlAlchemyDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, version_id: uuid.UUID) -> DocumentVersion | None:
        model = await self._session.get(DocumentVersionModel, version_id)
        return _version_to_entity(model) if model else None

    async def get_latest(self, document_id: uuid.UUID) -> DocumentVersion | None:
        stmt = (
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _version_to_entity(model) if model else None

    async def add(self, version: DocumentVersion) -> DocumentVersion:
        model = DocumentVersionModel(
            id=version.id,
            document_id=version.document_id,
            version_number=version.version_number,
            storage_key=version.storage_key,
            checksum_sha256=version.checksum_sha256,
            content_type=version.content_type,
            size_bytes=version.size_bytes,
            status=version.status.value,
            created_by=version.created_by,
            comment=version.comment,
            created_at=version.created_at,
            updated_at=version.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _version_to_entity(model)

    async def update(self, version: DocumentVersion) -> DocumentVersion:
        model = await self._session.get(DocumentVersionModel, version_id := version.id)
        if model is None:
            raise ValueError(f"Document version {version_id} not found")
        _apply_version(model, version)
        await self._session.flush()
        return _version_to_entity(model)

    async def list_for_document(self, document_id: uuid.UUID) -> list[DocumentVersion]:
        stmt = (
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_number.desc())
        )
        result = await self._session.execute(stmt)
        return [_version_to_entity(row) for row in result.scalars().all()]


class SqlAlchemyDocumentLockRepository(DocumentLockRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_for_document(self, document_id: uuid.UUID) -> DocumentLock | None:
        stmt = select(DocumentLockModel).where(DocumentLockModel.document_id == document_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        lock = _lock_to_entity(model)
        return lock if lock.is_active() else None

    async def add(self, lock: DocumentLock) -> DocumentLock:
        model = DocumentLockModel(
            id=lock.id,
            document_id=lock.document_id,
            locked_by=lock.locked_by,
            locked_at=lock.locked_at,
            expires_at=lock.expires_at,
            created_at=lock.created_at,
            updated_at=lock.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _lock_to_entity(model)

    async def delete(self, lock_id: uuid.UUID) -> None:
        model = await self._session.get(DocumentLockModel, lock_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
