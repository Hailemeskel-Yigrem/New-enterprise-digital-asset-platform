"""Download and versioning business rules for document assets."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from vaultforge.core.exceptions import AuthorizationError, ValidationError
from vaultforge.domain.assets.entities import Document, DocumentVersion
from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel, VersionStatus
from vaultforge.domain.common import utc_now
from vaultforge.domain.sharing.enums import SharePermission

MAX_DOWNLOAD_BYTES: dict[SensitivityLabel, int] = {
    SensitivityLabel.PUBLIC: 512 * 1024 * 1024,
    SensitivityLabel.INTERNAL: 256 * 1024 * 1024,
    SensitivityLabel.CONFIDENTIAL: 128 * 1024 * 1024,
    SensitivityLabel.RESTRICTED: 64 * 1024 * 1024,
}

VERSION_RETENTION_DAYS: dict[SensitivityLabel, int] = {
    SensitivityLabel.PUBLIC: 30,
    SensitivityLabel.INTERNAL: 90,
    SensitivityLabel.CONFIDENTIAL: 365,
    SensitivityLabel.RESTRICTED: 730,
}


@dataclass(frozen=True, slots=True)
class DownloadPolicyContext:
    user_id: uuid.UUID
    granted_permission: SharePermission | None
    is_org_member: bool
    watermark_required: bool = False
    legal_hold_active: bool = False


@dataclass(frozen=True, slots=True)
class DownloadDecision:
    allowed: bool
    reason: str
    apply_watermark: bool = False
    audit_level: str = "standard"


@dataclass(frozen=True, slots=True)
class VersioningPolicyContext:
    organization_id: uuid.UUID
    require_approval: bool = False
    max_versions: int = 50


@dataclass(frozen=True, slots=True)
class VersioningDecision:
    allowed: bool
    next_version_number: int
    supersede_current: bool
    reason: str


class DocumentDownloadPolicy:
    """Evaluate whether a user may download a specific document version."""

    def evaluate(
        self,
        document: Document,
        version: DocumentVersion,
        context: DownloadPolicyContext,
    ) -> DownloadDecision:
        if document.status == DocumentStatus.DELETED:
            return DownloadDecision(False, "Document has been deleted")

        if version.status not in {VersionStatus.CURRENT, VersionStatus.SUPERSEDED}:
            return DownloadDecision(False, "Version is not available for download")

        if version.document_id != document.id:
            return DownloadDecision(False, "Version does not belong to document")

        max_bytes = MAX_DOWNLOAD_BYTES.get(document.sensitivity, 128 * 1024 * 1024)
        if version.size_bytes > max_bytes and not context.is_org_member:
            return DownloadDecision(False, "External download exceeds sensitivity size cap")

        if context.granted_permission is None and not context.is_org_member:
            return DownloadDecision(False, "No download permission")

        if (
            context.granted_permission is not None
            and context.granted_permission
            not in {SharePermission.DOWNLOAD, SharePermission.EDIT, SharePermission.ADMIN}
            and not _admin_share(context.granted_permission)
        ):
            return DownloadDecision(False, "Share grant does not include download")

        watermark = context.watermark_required or document.sensitivity in {
            SensitivityLabel.CONFIDENTIAL,
            SensitivityLabel.RESTRICTED,
        }

        audit = "elevated" if document.sensitivity == SensitivityLabel.RESTRICTED else "standard"
        if context.legal_hold_active:
            audit = "legal_hold"

        return DownloadDecision(
            allowed=True,
            reason="Download permitted",
            apply_watermark=watermark,
            audit_level=audit,
        )


class DocumentVersioningPolicy:
    """Rules governing creation and retention of document versions."""

    def __init__(self, context: VersioningPolicyContext) -> None:
        self._context = context

    def evaluate_new_version(
        self,
        document: Document,
        existing_versions: list[DocumentVersion],
        *,
        proposed_size_bytes: int,
    ) -> VersioningDecision:
        if document.status == DocumentStatus.DELETED:
            return VersioningDecision(False, 0, False, "Cannot version deleted document")

        if document.status == DocumentStatus.ARCHIVED:
            return VersioningDecision(False, 0, False, "Archived documents are immutable")

        active_versions = [v for v in existing_versions if v.status != VersionStatus.PENDING]
        if len(active_versions) >= self._context.max_versions:
            return VersioningDecision(
                False,
                0,
                False,
                f"Maximum {self._context.max_versions} versions reached",
            )

        if proposed_size_bytes <= 0:
            raise ValidationError("Version payload must be positive size")

        next_number = max((v.version_number for v in active_versions), default=0) + 1
        supersede = any(v.status == VersionStatus.CURRENT for v in active_versions)

        if self._context.require_approval:
            return VersioningDecision(
                True,
                next_number,
                supersede,
                "Version queued pending approval",
            )

        return VersioningDecision(
            True,
            next_number,
            supersede,
            "Version may be uploaded",
        )

    def versions_eligible_for_purge(
        self,
        document: Document,
        versions: list[DocumentVersion],
        *,
        at: datetime | None = None,
    ) -> list[DocumentVersion]:
        reference = at or utc_now()
        retention_days = VERSION_RETENTION_DAYS.get(document.sensitivity, 90)
        cutoff = reference - timedelta(days=retention_days)
        eligible: list[DocumentVersion] = []
        for version in versions:
            if version.status != VersionStatus.SUPERSEDED:
                continue
            if version.updated_at > cutoff:
                continue
            if document.current_version_id == version.id:
                continue
            eligible.append(version)
        return eligible


def enforce_download_or_raise(
    document: Document,
    version: DocumentVersion,
    context: DownloadPolicyContext,
) -> DownloadDecision:
    decision = DocumentDownloadPolicy().evaluate(document, version, context)
    if not decision.allowed:
        raise AuthorizationError(decision.reason)
    return decision


def _admin_share(permission: SharePermission) -> bool:
    return permission == SharePermission.ADMIN


@dataclass(frozen=True, slots=True)
class UploadPolicyContext:
    user_id: uuid.UUID
    is_org_member: bool
    max_upload_bytes: int = 256 * 1024 * 1024
    blocked_extensions: frozenset[str] = frozenset({".exe", ".bat", ".cmd", ".scr"})


@dataclass(frozen=True, slots=True)
class UploadDecision:
    allowed: bool
    reason: str
    scan_required: bool = True


class DocumentUploadPolicy:
    """Validate whether an upload payload may be accepted."""

    def evaluate(
        self,
        document: Document,
        *,
        filename: str,
        size_bytes: int,
        content_type: str,
        context: UploadPolicyContext,
    ) -> UploadDecision:
        if document.status == DocumentStatus.DELETED:
            return UploadDecision(False, "Cannot upload to deleted document", False)

        if not context.is_org_member:
            return UploadDecision(False, "External uploads require membership", False)

        if size_bytes <= 0:
            return UploadDecision(False, "Empty uploads are rejected", False)

        if size_bytes > context.max_upload_bytes:
            return UploadDecision(False, "Upload exceeds size limit", False)

        lowered = filename.lower()
        for ext in context.blocked_extensions:
            if lowered.endswith(ext):
                return UploadDecision(False, f"Extension {ext} is blocked", False)

        if not content_type or content_type == "application/octet-stream":
            return UploadDecision(True, "Upload accepted with generic content type", True)

        return UploadDecision(True, "Upload accepted", True)


def evaluate_upload_or_raise(
    document: Document,
    *,
    filename: str,
    size_bytes: int,
    content_type: str,
    context: UploadPolicyContext,
) -> UploadDecision:
    decision = DocumentUploadPolicy().evaluate(
        document,
        filename=filename,
        size_bytes=size_bytes,
        content_type=content_type,
        context=context,
    )
    if not decision.allowed:
        raise ValidationError(decision.reason)
    return decision
