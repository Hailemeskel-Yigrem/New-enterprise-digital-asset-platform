"""Bulk asset operations: move, delete, retag with validation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.domain.assets.entities import Document
from vaultforge.domain.assets.enums import DocumentStatus
from vaultforge.domain.assets.metadata_repositories import MetadataValueRepository
from vaultforge.domain.assets.repositories import DocumentRepository, FolderRepository
from vaultforge.domain.compliance.repositories import ComplianceHoldRepository


class BulkOperationType(StrEnum):
    MOVE = "move"
    DELETE = "delete"
    RETAG = "retag"
    ARCHIVE = "archive"


@dataclass(frozen=True, slots=True)
class BulkOperationItem:
    resource_id: uuid.UUID
    resource_type: str = "document"


@dataclass(frozen=True, slots=True)
class BulkMoveOptions:
    target_folder_id: uuid.UUID | None
    skip_on_hold: bool = True
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class BulkDeleteOptions:
    permanent: bool = False
    skip_on_hold: bool = True
    dry_run: bool = False


@dataclass(frozen=True, slots=True)
class BulkRetagOptions:
    add_tags: frozenset[str] = frozenset()
    remove_tags: frozenset[str] = frozenset()
    replace_tags: frozenset[str] | None = None
    dry_run: bool = False


@dataclass(slots=True)
class BulkOperationResult:
    operation: BulkOperationType
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
    dry_run: bool = False

    def record_success(self) -> None:
        self.succeeded += 1

    def record_failure(self, resource_id: uuid.UUID, message: str) -> None:
        self.failed += 1
        self.errors.append({"resource_id": str(resource_id), "message": message[:500]})

    def record_skip(self, resource_id: uuid.UUID, reason: str) -> None:
        self.skipped += 1
        self.errors.append({"resource_id": str(resource_id), "message": f"skipped: {reason}"})


@dataclass(slots=True)
class BulkOperationsService:
    documents: DocumentRepository
    folders: FolderRepository
    metadata_values: MetadataValueRepository
    holds: ComplianceHoldRepository

    async def move_documents(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        items: list[BulkOperationItem],
        options: BulkMoveOptions,
    ) -> BulkOperationResult:
        result = BulkOperationResult(
            BulkOperationType.MOVE, total=len(items), dry_run=options.dry_run
        )
        target_folder_id = options.target_folder_id
        if target_folder_id is not None:
            folder = await self.folders.get_by_id(organization_id, target_folder_id)
            if folder is None:
                raise NotFoundError("Target folder not found")
        for item in items:
            try:
                doc = await self._get_document(organization_id, item.resource_id)
                if options.skip_on_hold and await self._is_on_hold(organization_id, doc):
                    result.record_skip(item.resource_id, "legal hold")
                    continue
                if options.dry_run:
                    result.record_success()
                    continue
                if target_folder_id is None:
                    result.record_skip(item.resource_id, "no target folder specified")
                    continue
                doc.folder_id = target_folder_id
                doc.touch()
                await self.documents.update(doc)
                result.record_success()
            except ValidationError as exc:
                result.record_failure(item.resource_id, exc.message)
        return result

    async def delete_documents(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        items: list[BulkOperationItem],
        options: BulkDeleteOptions,
    ) -> BulkOperationResult:
        result = BulkOperationResult(
            BulkOperationType.DELETE, total=len(items), dry_run=options.dry_run
        )
        for item in items:
            try:
                doc = await self._get_document(organization_id, item.resource_id)
                if options.skip_on_hold and await self._is_on_hold(organization_id, doc):
                    result.record_skip(item.resource_id, "legal hold")
                    continue
                if options.dry_run:
                    result.record_success()
                    continue
                doc.soft_delete()
                await self.documents.update(doc)
                if options.permanent:
                    await self.metadata_values.delete_for_resource(
                        organization_id, "document", doc.id
                    )
                result.record_success()
            except ValidationError as exc:
                result.record_failure(item.resource_id, exc.message)
        return result

    async def retag_documents(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        items: list[BulkOperationItem],
        options: BulkRetagOptions,
    ) -> BulkOperationResult:
        result = BulkOperationResult(
            BulkOperationType.RETAG, total=len(items), dry_run=options.dry_run
        )
        for item in items:
            try:
                doc = await self._get_document(organization_id, item.resource_id)
                new_tags = self._compute_tags(doc.tags, options)
                if options.dry_run:
                    result.record_success()
                    continue
                doc.tags = sorted(new_tags)
                doc.touch()
                await self.documents.update(doc)
                result.record_success()
            except ValidationError as exc:
                result.record_failure(item.resource_id, exc.message)
        return result

    async def _get_document(self, organization_id: uuid.UUID, document_id: uuid.UUID) -> Document:
        doc = await self.documents.get_by_id(organization_id, document_id)
        if doc is None:
            raise NotFoundError(f"Document not found: {document_id}")
        if doc.status == DocumentStatus.DELETED:
            raise ValidationError("Cannot operate on deleted document")
        return doc

    async def _is_on_hold(self, organization_id: uuid.UUID, doc: Document) -> bool:
        holds = await self.holds.list_active_for_resource(organization_id, doc.id, doc.folder_id)
        return len(holds) > 0

    @staticmethod
    def _compute_tags(current: list[str], options: BulkRetagOptions) -> set[str]:
        if options.replace_tags is not None:
            tags = set(options.replace_tags)
        else:
            tags = set(current)
            tags |= options.add_tags
            tags -= options.remove_tags
        normalized = {t.strip().lower() for t in tags if t.strip()}
        if len(normalized) > 50:
            raise ValidationError("Maximum 50 tags per document")
        return normalized
