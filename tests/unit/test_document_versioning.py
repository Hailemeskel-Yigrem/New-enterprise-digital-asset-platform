"""Unit tests for document versioning and checkout rules."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import ConflictError, ValidationError
from vaultforge.domain.assets.entities import Document, DocumentLock, DocumentVersion
from vaultforge.domain.assets.enums import DocumentStatus, VersionStatus


def test_document_version_starts_at_one() -> None:
    version = DocumentVersion(document_id=uuid.uuid4(), version_number=1)
    assert version.version_number == 1
    assert version.status == VersionStatus.CURRENT


def test_attach_version_sets_current_and_activates_draft() -> None:
    document = Document(name="Policy.pdf", status=DocumentStatus.DRAFT)
    version = DocumentVersion(document_id=document.id, version_number=1)
    document.attach_version(version)
    assert document.current_version_id == version.id
    assert document.status == DocumentStatus.ACTIVE


def test_attach_version_rejects_foreign_version() -> None:
    document = Document(name="Policy.pdf")
    foreign = DocumentVersion(document_id=uuid.uuid4(), version_number=1)
    with pytest.raises(ValidationError, match="does not belong"):
        document.attach_version(foreign)


def test_supersede_marks_version_status() -> None:
    version = DocumentVersion(version_number=1, status=VersionStatus.CURRENT)
    version.mark_superseded()
    assert version.status == VersionStatus.SUPERSEDED


def test_checkout_blocked_when_active_lock_exists() -> None:
    document = Document(name="Contract.docx", status=DocumentStatus.ACTIVE)
    lock = DocumentLock(document_id=document.id, locked_by=uuid.uuid4())
    with pytest.raises(ConflictError, match="checked out"):
        document.ensure_checkout_allowed(lock)


def test_checkin_requires_lock_owner() -> None:
    document = Document(name="Contract.docx", status=DocumentStatus.ACTIVE)
    owner = uuid.uuid4()
    other = uuid.uuid4()
    lock = DocumentLock(document_id=document.id, locked_by=owner)
    with pytest.raises(ConflictError, match="Only the user"):
        document.checkin(lock, other)


def test_soft_delete_marks_deleted_timestamp() -> None:
    document = Document(name="Old.pdf", status=DocumentStatus.ACTIVE)
    document.soft_delete()
    assert document.status == DocumentStatus.DELETED
    assert document.deleted_at is not None
