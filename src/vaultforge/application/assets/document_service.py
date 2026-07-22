"""Document lifecycle application service."""

from __future__ import annotations

import hashlib
import uuid

from vaultforge.application.assets.schemas import (
    CheckoutResponse,
    DocumentDownloadResult,
    DocumentResponse,
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentVersionCreateRequest,
    DocumentVersionResponse,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError, ValidationError
from vaultforge.core.pagination import Page, PageParams
from vaultforge.domain.assets.entities import Document, DocumentVersion
from vaultforge.domain.assets.enums import VersionStatus
from vaultforge.domain.assets.repositories import (
    DocumentLockRepository,
    DocumentRepository,
    DocumentVersionRepository,
    FolderRepository,
)
from vaultforge.infrastructure.storage.base import StorageBackend


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_storage_key(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    version_number: int,
    filename: str,
) -> str:
    safe_name = filename.replace("\\", "_").replace("/", "_")
    return f"{organization_id}/{document_id}/v{version_number}/{safe_name}"


class DocumentService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        version_repo: DocumentVersionRepository,
        lock_repo: DocumentLockRepository,
        folder_repo: FolderRepository,
        storage: StorageBackend,
    ) -> None:
        self._documents = document_repo
        self._versions = version_repo
        self._locks = lock_repo
        self._folders = folder_repo
        self._storage = storage

    async def upload_document(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: DocumentUploadRequest,
        *,
        content: bytes,
        content_type: str,
    ) -> DocumentResponse:
        folder = await self._folders.get_by_id(organization_id, payload.folder_id)
        if folder is None:
            raise NotFoundError("Folder not found")
        if not content:
            raise ValidationError("Document content cannot be empty")

        document = Document(
            organization_id=organization_id,
            folder_id=payload.folder_id,
            name=payload.name.strip(),
            sensitivity=payload.sensitivity,
            tags=sorted({tag.strip().lower() for tag in payload.tags if tag.strip()}),
            created_by=user_id,
        )
        saved_document = await self._documents.add(document)

        version = DocumentVersion(
            document_id=saved_document.id,
            version_number=1,
            storage_key=_build_storage_key(
                organization_id, saved_document.id, 1, saved_document.name
            ),
            checksum_sha256=_sha256(content),
            content_type=content_type,
            size_bytes=len(content),
            status=VersionStatus.CURRENT,
            created_by=user_id,
            comment=payload.comment.strip(),
        )
        await self._storage.put(version.storage_key, content, content_type=content_type)
        saved_version = await self._versions.add(version)

        saved_document.attach_version(saved_version)
        saved_document = await self._documents.update(saved_document)
        return await self._to_response(saved_document, saved_version)

    async def create_version(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: DocumentVersionCreateRequest,
        *,
        content: bytes,
        content_type: str,
    ) -> DocumentResponse:
        document = await self._require_document(organization_id, document_id)
        active_lock = await self._locks.get_active_for_document(document.id)
        if active_lock is not None and active_lock.locked_by != user_id:
            raise ConflictError("Document is checked out by another user")
        if not content:
            raise ValidationError("Document content cannot be empty")

        latest = await self._versions.get_latest(document.id)
        next_number = 1 if latest is None else latest.version_number + 1

        if latest is not None and latest.status == VersionStatus.CURRENT:
            latest.mark_superseded()
            await self._versions.update(latest)

        version = DocumentVersion(
            document_id=document.id,
            version_number=next_number,
            storage_key=_build_storage_key(
                organization_id, document.id, next_number, document.name
            ),
            checksum_sha256=_sha256(content),
            content_type=content_type,
            size_bytes=len(content),
            status=VersionStatus.CURRENT,
            created_by=user_id,
            comment=payload.comment.strip(),
        )
        await self._storage.put(version.storage_key, content, content_type=content_type)
        saved_version = await self._versions.add(version)

        document.attach_version(saved_version)
        saved_document = await self._documents.update(document)
        if active_lock is not None:
            await self._locks.delete(active_lock.id)
        return await self._to_response(saved_document, saved_version)

    async def checkout(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> CheckoutResponse:
        document = await self._require_document(organization_id, document_id)
        active_lock = await self._locks.get_active_for_document(document.id)
        document.ensure_checkout_allowed(active_lock)
        lock = document.checkout(user_id)
        saved_lock = await self._locks.add(lock)
        return CheckoutResponse(
            lock_id=saved_lock.id,
            document_id=saved_lock.document_id,
            locked_by=saved_lock.locked_by,
            locked_at=saved_lock.locked_at,
            expires_at=saved_lock.expires_at,
        )

    async def checkin(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> DocumentResponse:
        document = await self._require_document(organization_id, document_id)
        active_lock = await self._locks.get_active_for_document(document.id)
        if active_lock is None:
            raise ConflictError("Document is not checked out")
        document.checkin(active_lock, user_id)
        await self._locks.delete(active_lock.id)
        saved_document = await self._documents.update(document)
        current_version = None
        if saved_document.current_version_id is not None:
            current_version = await self._versions.get_by_id(saved_document.current_version_id)
        return await self._to_response(saved_document, current_version)

    async def soft_delete(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentResponse:
        document = await self._require_document(organization_id, document_id)
        active_lock = await self._locks.get_active_for_document(document.id)
        if active_lock is not None:
            raise ConflictError("Cannot delete a checked-out document")
        document.soft_delete()
        saved_document = await self._documents.update(document)
        current_version = None
        if saved_document.current_version_id is not None:
            current_version = await self._versions.get_by_id(saved_document.current_version_id)
        return await self._to_response(saved_document, current_version)

    async def get_document(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentResponse:
        document = await self._require_document(organization_id, document_id)
        current_version = None
        if document.current_version_id is not None:
            current_version = await self._versions.get_by_id(document.current_version_id)
        return await self._to_response(document, current_version)

    async def update_document(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        payload: DocumentUpdateRequest,
    ) -> DocumentResponse:
        document = await self._require_document(organization_id, document_id)
        active_lock = await self._locks.get_active_for_document(document.id)
        if active_lock is not None:
            raise ConflictError("Cannot update metadata while document is checked out")
        if payload.name is not None:
            document.rename(payload.name)
        if payload.sensitivity is not None:
            document.sensitivity = payload.sensitivity
            document.touch()
        if payload.tags is not None:
            document.set_tags(payload.tags)
        saved_document = await self._documents.update(document)
        current_version = None
        if saved_document.current_version_id is not None:
            current_version = await self._versions.get_by_id(saved_document.current_version_id)
        return await self._to_response(saved_document, current_version)

    async def archive_document(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> DocumentResponse:
        document = await self._require_document(organization_id, document_id)
        active_lock = await self._locks.get_active_for_document(document.id)
        if active_lock is not None:
            raise ConflictError("Cannot archive a checked-out document")
        document.archive()
        saved_document = await self._documents.update(document)
        current_version = None
        if saved_document.current_version_id is not None:
            current_version = await self._versions.get_by_id(saved_document.current_version_id)
        return await self._to_response(saved_document, current_version)

    async def list_versions(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        params: PageParams | None = None,
    ) -> Page[DocumentVersionResponse]:
        document = await self._require_document(organization_id, document_id)
        page_params = params or PageParams()
        versions = list(await self._versions.list_for_document(document.id))
        total = len(versions)
        start = page_params.offset
        end = start + page_params.limit
        slice_ = versions[start:end]
        items = [DocumentVersionResponse.model_validate(v) for v in slice_]
        return Page.build(items, total=total, params=page_params)

    async def download_content(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        version_id: uuid.UUID | None = None,
    ) -> DocumentDownloadResult:
        document = await self._require_document(organization_id, document_id)
        target_version_id = version_id or document.current_version_id
        if target_version_id is None:
            raise NotFoundError("Document has no downloadable version")
        version = await self._versions.get_by_id(target_version_id)
        if version is None or version.document_id != document.id:
            raise NotFoundError("Document version not found")
        data = await self._storage.get(version.storage_key)
        return DocumentDownloadResult(
            document_id=document.id,
            version_id=version.id,
            filename=document.name,
            content_type=version.content_type,
            size_bytes=version.size_bytes,
            checksum_sha256=version.checksum_sha256,
            data=data,
        )

    async def _require_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document:
        document = await self._documents.get_by_id(organization_id, document_id)
        if document is None:
            raise NotFoundError("Document not found")
        return document

    async def _to_response(
        self,
        document: Document,
        version: DocumentVersion | None,
    ) -> DocumentResponse:
        version_response = (
            DocumentVersionResponse.model_validate(version) if version is not None else None
        )
        return DocumentResponse(
            id=document.id,
            organization_id=document.organization_id,
            folder_id=document.folder_id,
            name=document.name,
            status=document.status,
            sensitivity=document.sensitivity,
            tags=document.tags,
            current_version_id=document.current_version_id,
            created_by=document.created_by,
            deleted_at=document.deleted_at,
            created_at=document.created_at,
            updated_at=document.updated_at,
            current_version=version_response,
        )
