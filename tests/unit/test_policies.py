"""Unit tests for document download and versioning policies."""

from __future__ import annotations

import uuid
from datetime import timedelta

from vaultforge.core.exceptions import AuthorizationError
from vaultforge.domain.assets.entities import Document, DocumentVersion
from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel, VersionStatus
from vaultforge.domain.assets.policies import (
    DocumentDownloadPolicy,
    DocumentVersioningPolicy,
    DownloadPolicyContext,
    VersioningPolicyContext,
    enforce_download_or_raise,
)
from vaultforge.domain.common import utc_now
from vaultforge.domain.sharing.enums import SharePermission


def _document(**overrides: object) -> Document:
    data = {
        "organization_id": uuid.uuid4(),
        "folder_id": uuid.uuid4(),
        "name": "Policy Doc",
        "status": DocumentStatus.ACTIVE,
        "sensitivity": SensitivityLabel.INTERNAL,
        "created_by": uuid.uuid4(),
        "current_version_id": uuid.uuid4(),
    }
    data.update(overrides)
    return Document(**data)


def _version(document: Document, **overrides: object) -> DocumentVersion:
    data = {
        "document_id": document.id,
        "version_number": 1,
        "storage_key": "key",
        "checksum_sha256": "abc",
        "content_type": "application/pdf",
        "size_bytes": 1024,
        "status": VersionStatus.CURRENT,
        "created_by": document.created_by,
    }
    data.update(overrides)
    return DocumentVersion(**data)


def test_download_allowed_for_org_member() -> None:
    doc = _document()
    version = _version(doc)
    ctx = DownloadPolicyContext(
        user_id=uuid.uuid4(),
        granted_permission=None,
        is_org_member=True,
    )
    decision = DocumentDownloadPolicy().evaluate(doc, version, ctx)
    assert decision.allowed is True
    assert decision.apply_watermark is False


def test_download_denied_for_deleted_document() -> None:
    doc = _document(status=DocumentStatus.DELETED)
    version = _version(doc)
    ctx = DownloadPolicyContext(
        user_id=uuid.uuid4(),
        granted_permission=SharePermission.DOWNLOAD,
        is_org_member=True,
    )
    decision = DocumentDownloadPolicy().evaluate(doc, version, ctx)
    assert decision.allowed is False


def test_restricted_document_requires_watermark() -> None:
    doc = _document(sensitivity=SensitivityLabel.RESTRICTED)
    version = _version(doc)
    ctx = DownloadPolicyContext(
        user_id=uuid.uuid4(),
        granted_permission=SharePermission.DOWNLOAD,
        is_org_member=True,
    )
    decision = DocumentDownloadPolicy().evaluate(doc, version, ctx)
    assert decision.allowed is True
    assert decision.apply_watermark is True
    assert decision.audit_level == "elevated"


def test_enforce_download_raises_on_denial() -> None:
    doc = _document(status=DocumentStatus.DELETED)
    version = _version(doc)
    ctx = DownloadPolicyContext(
        user_id=uuid.uuid4(),
        granted_permission=None,
        is_org_member=False,
    )
    try:
        enforce_download_or_raise(doc, version, ctx)
        raise AssertionError("expected AuthorizationError")
    except AuthorizationError:
        pass


def test_versioning_rejects_archived_document() -> None:
    doc = _document(status=DocumentStatus.ARCHIVED)
    policy = DocumentVersioningPolicy(VersioningPolicyContext(organization_id=doc.organization_id))
    decision = policy.evaluate_new_version(doc, [], proposed_size_bytes=100)
    assert decision.allowed is False


def test_versioning_increments_version_number() -> None:
    doc = _document()
    existing = [_version(doc, version_number=1, status=VersionStatus.CURRENT)]
    policy = DocumentVersioningPolicy(VersioningPolicyContext(organization_id=doc.organization_id))
    decision = policy.evaluate_new_version(doc, existing, proposed_size_bytes=2048)
    assert decision.allowed is True
    assert decision.next_version_number == 2
    assert decision.supersede_current is True


def test_versions_eligible_for_purge_respects_retention() -> None:
    doc = _document(sensitivity=SensitivityLabel.PUBLIC)
    old = _version(
        doc,
        version_number=1,
        status=VersionStatus.SUPERSEDED,
    )
    old.updated_at = utc_now() - timedelta(days=120)
    current = _version(doc, version_number=2, status=VersionStatus.CURRENT)
    policy = DocumentVersioningPolicy(VersioningPolicyContext(organization_id=doc.organization_id))
    eligible = policy.versions_eligible_for_purge(doc, [old, current])
    assert old in eligible
    assert current not in eligible

from vaultforge.domain.assets.policies import (
    DocumentUploadPolicy,
    UploadPolicyContext,
    evaluate_upload_or_raise,
)


def test_upload_policy_blocks_executable() -> None:
    doc = _document()
    ctx = UploadPolicyContext(user_id=uuid.uuid4(), is_org_member=True)
    decision = DocumentUploadPolicy().evaluate(
        doc,
        filename="malware.exe",
        size_bytes=1024,
        content_type="application/octet-stream",
        context=ctx,
    )
    assert decision.allowed is False


def test_upload_policy_allows_pdf_for_member() -> None:
    doc = _document()
    ctx = UploadPolicyContext(user_id=uuid.uuid4(), is_org_member=True)
    decision = evaluate_upload_or_raise(
        doc,
        filename="contract.pdf",
        size_bytes=4096,
        content_type="application/pdf",
        context=ctx,
    )
    assert decision.allowed is True
    assert decision.scan_required is True

def test_upload_oversized_rejected() -> None:
    doc = _document()
    ctx = UploadPolicyContext(
        user_id=uuid.uuid4(),
        is_org_member=True,
        max_upload_bytes=1024,
    )
    decision = DocumentUploadPolicy().evaluate(
        doc,
        filename="large.bin",
        size_bytes=2048,
        content_type="application/octet-stream",
        context=ctx,
    )
    assert decision.allowed is False
    assert "size" in decision.reason.lower()


def test_upload_non_member_denied() -> None:
    doc = _document()
    ctx = UploadPolicyContext(user_id=uuid.uuid4(), is_org_member=False)
    decision = DocumentUploadPolicy().evaluate(
        doc,
        filename="doc.pdf",
        size_bytes=512,
        content_type="application/pdf",
        context=ctx,
    )
    assert decision.allowed is False
