"""Unit tests for DocumentService business rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.assets.document_service import DocumentService
from vaultforge.application.assets.schemas import (
    DocumentUpdateRequest,
    DocumentUploadRequest,
    DocumentVersionCreateRequest,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError, ValidationError
from vaultforge.domain.assets.entities import Document, DocumentLock, DocumentVersion, Folder
from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel, VersionStatus


def _now() -> datetime:
    return datetime.now(UTC)


def _folder(org_id: uuid.UUID | None = None) -> Folder:
    return Folder(
        id=uuid.uuid4(),
        organization_id=org_id or uuid.uuid4(),
        name="Contracts",
        created_at=_now(),
        updated_at=_now(),
    )


def _document(**overrides: object) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        folder_id=uuid.uuid4(),
        name="Policy.pdf",
        status=DocumentStatus.ACTIVE,
        created_by=uuid.uuid4(),
        created_at=_now(),
        updated_at=_now(),
    )
    for key, value in overrides.items():
        setattr(doc, key, value)
    return doc


def _service(**mocks: AsyncMock) -> DocumentService:
    return DocumentService(
        document_repo=mocks.get("documents", AsyncMock()),
        version_repo=mocks.get("versions", AsyncMock()),
        lock_repo=mocks.get("locks", AsyncMock()),
        folder_repo=mocks.get("folders", AsyncMock()),
        storage=mocks.get("storage", AsyncMock()),
    )


@pytest.mark.asyncio
async def test_upload_rejects_missing_folder() -> None:
    folders = AsyncMock()
    folders.get_by_id = AsyncMock(return_value=None)
    service = _service(folders=folders)

    with pytest.raises(NotFoundError, match="Folder not found"):
        await service.upload_document(
            uuid.uuid4(),
            uuid.uuid4(),
            DocumentUploadRequest(folder_id=uuid.uuid4(), name="file.pdf"),
            content=b"data",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_upload_rejects_empty_content() -> None:
    folder = _folder()
    folders = AsyncMock()
    folders.get_by_id = AsyncMock(return_value=folder)
    service = _service(folders=folders)

    with pytest.raises(ValidationError, match="empty"):
        await service.upload_document(
            folder.organization_id,
            uuid.uuid4(),
            DocumentUploadRequest(folder_id=folder.id, name="file.pdf"),
            content=b"",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_create_version_blocked_when_locked_by_other_user() -> None:
    document = _document()
    other_user = uuid.uuid4()
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(
        return_value=DocumentLock(document_id=document.id, locked_by=other_user)
    )
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    service = _service(documents=documents, locks=locks)

    with pytest.raises(ConflictError, match="checked out"):
        await service.create_version(
            document.organization_id,
            document.id,
            uuid.uuid4(),
            DocumentVersionCreateRequest(comment="v2"),
            content=b"v2",
            content_type="application/pdf",
        )


@pytest.mark.asyncio
async def test_soft_delete_blocked_when_checked_out() -> None:
    document = _document()
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(
        return_value=DocumentLock(document_id=document.id, locked_by=uuid.uuid4())
    )
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    service = _service(documents=documents, locks=locks)

    with pytest.raises(ConflictError, match="checked-out"):
        await service.soft_delete(document.organization_id, document.id)


@pytest.mark.asyncio
async def test_update_metadata_blocked_during_checkout() -> None:
    document = _document()
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(
        return_value=DocumentLock(document_id=document.id, locked_by=uuid.uuid4())
    )
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    service = _service(documents=documents, locks=locks)

    with pytest.raises(ConflictError, match="checked out"):
        await service.update_document(
            document.organization_id,
            document.id,
            DocumentUpdateRequest(name="Renamed.pdf"),
        )


@pytest.mark.asyncio
async def test_download_requires_version() -> None:
    document = _document(current_version_id=None)
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    service = _service(documents=documents)

    with pytest.raises(NotFoundError, match="no downloadable version"):
        await service.download_content(document.organization_id, document.id)


@pytest.mark.asyncio
async def test_list_versions_paginates() -> None:
    document = _document()
    versions = [
        DocumentVersion(
            id=uuid.uuid4(),
            document_id=document.id,
            version_number=n,
            status=VersionStatus.CURRENT if n == 2 else VersionStatus.SUPERSEDED,
            created_at=_now(),
            updated_at=_now(),
        )
        for n in (1, 2)
    ]
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    version_repo = AsyncMock()
    version_repo.list_for_document = AsyncMock(return_value=versions)
    service = _service(documents=documents, versions=version_repo)

    from vaultforge.core.pagination import PageParams

    page = await service.list_versions(
        document.organization_id,
        document.id,
        params=PageParams(page=1, page_size=1),
    )

    assert page.total == 2
    assert len(page.items) == 1
    assert page.items[0].version_number in {1, 2}


@pytest.mark.asyncio
async def test_upload_normalizes_tags_and_stores_version() -> None:
    folder = _folder()
    org_id = folder.organization_id
    user_id = uuid.uuid4()
    folders = AsyncMock()
    folders.get_by_id = AsyncMock(return_value=folder)
    documents = AsyncMock()

    async def _add_doc(doc):
        return doc

    documents.add = AsyncMock(side_effect=_add_doc)

    async def _upd_doc(doc):
        return doc

    documents.update = AsyncMock(side_effect=_upd_doc)
    versions = AsyncMock()

    async def _add_ver(ver):
        return ver

    versions.add = AsyncMock(side_effect=_add_ver)
    storage = AsyncMock()
    service = _service(folders=folders, documents=documents, versions=versions, storage=storage)

    response = await service.upload_document(
        org_id,
        user_id,
        DocumentUploadRequest(
            folder_id=folder.id,
            name="Report.pdf",
            tags=[" Legal ", "legal", "Q1"],
            sensitivity=SensitivityLabel.CONFIDENTIAL,
        ),
        content=b"body",
        content_type="application/pdf",
    )

    assert response.tags == ["legal", "q1"]
    storage.put.assert_awaited_once()
    versions.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_version_supersedes_current() -> None:
    document = _document()
    user_id = uuid.uuid4()
    current = DocumentVersion(
        id=uuid.uuid4(),
        document_id=document.id,
        version_number=1,
        status=VersionStatus.CURRENT,
        storage_key="old",
        created_at=_now(),
        updated_at=_now(),
    )
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    documents.update = AsyncMock(side_effect=lambda doc: doc)
    versions = AsyncMock()
    versions.get_latest = AsyncMock(return_value=current)
    versions.update = AsyncMock(side_effect=lambda ver: ver)
    versions.add = AsyncMock(side_effect=lambda ver: ver)
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(return_value=None)
    storage = AsyncMock()
    service = _service(documents=documents, versions=versions, locks=locks, storage=storage)

    response = await service.create_version(
        document.organization_id,
        document.id,
        user_id,
        DocumentVersionCreateRequest(comment="v2"),
        content=b"v2-body",
        content_type="application/pdf",
    )
    assert response.current_version is not None
    assert response.current_version.version_number == 2
    assert current.status == VersionStatus.SUPERSEDED
    storage.put.assert_awaited_once()


@pytest.mark.asyncio
async def test_checkout_and_checkin_flow() -> None:
    document = _document()
    user_id = uuid.uuid4()
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    documents.update = AsyncMock(side_effect=lambda doc: doc)
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(return_value=None)
    locks.add = AsyncMock(side_effect=lambda lock: lock)
    locks.delete = AsyncMock()
    versions = AsyncMock()
    versions.get_by_id = AsyncMock(return_value=None)
    service = _service(documents=documents, locks=locks, versions=versions)

    checkout = await service.checkout(document.organization_id, document.id, user_id)
    assert checkout.locked_by == user_id

    active = DocumentLock(document_id=document.id, locked_by=user_id)
    locks.get_active_for_document = AsyncMock(return_value=active)
    response = await service.checkin(document.organization_id, document.id, user_id)
    assert response.id == document.id
    locks.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_archive_and_soft_delete() -> None:
    document = _document()
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    documents.update = AsyncMock(side_effect=lambda doc: doc)
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(return_value=None)
    versions = AsyncMock()
    versions.get_by_id = AsyncMock(return_value=None)
    service = _service(documents=documents, locks=locks, versions=versions)

    archived = await service.archive_document(document.organization_id, document.id)
    assert archived.status == DocumentStatus.ARCHIVED

    document.status = DocumentStatus.ACTIVE
    deleted = await service.soft_delete(document.organization_id, document.id)
    assert deleted.status == DocumentStatus.DELETED


@pytest.mark.asyncio
async def test_update_document_applies_fields() -> None:
    document = _document()
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    documents.update = AsyncMock(side_effect=lambda doc: doc)
    locks = AsyncMock()
    locks.get_active_for_document = AsyncMock(return_value=None)
    versions = AsyncMock()
    versions.get_by_id = AsyncMock(return_value=None)
    service = _service(documents=documents, locks=locks, versions=versions)

    response = await service.update_document(
        document.organization_id,
        document.id,
        DocumentUpdateRequest(
            name="Renamed.pdf",
            sensitivity=SensitivityLabel.RESTRICTED,
            tags=["a", "B"],
        ),
    )
    assert response.name == "Renamed.pdf"
    assert response.sensitivity == SensitivityLabel.RESTRICTED
    assert response.tags == ["a", "b"]


@pytest.mark.asyncio
async def test_download_content_success() -> None:
    version_id = uuid.uuid4()
    document = _document(current_version_id=version_id, name="file.pdf")
    version = DocumentVersion(
        id=version_id,
        document_id=document.id,
        version_number=1,
        storage_key="org/doc/v1/file.pdf",
        content_type="application/pdf",
        size_bytes=4,
        checksum_sha256="abcd",
        created_at=_now(),
        updated_at=_now(),
    )
    documents = AsyncMock()
    documents.get_by_id = AsyncMock(return_value=document)
    versions = AsyncMock()
    versions.get_by_id = AsyncMock(return_value=version)
    storage = AsyncMock()
    storage.get = AsyncMock(return_value=b"data")
    service = _service(documents=documents, versions=versions, storage=storage)

    result = await service.download_content(document.organization_id, document.id)
    assert result.data == b"data"
    assert result.filename == "file.pdf"
    assert result.version_id == version_id
