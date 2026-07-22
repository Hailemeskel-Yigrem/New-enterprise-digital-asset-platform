"""Export and import job persistence repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.jobs.export_service import ExportFormat, ExportJob, ExportJobStatus
from vaultforge.application.jobs.import_service import ImportJob, ImportJobStatus
from vaultforge.infrastructure.persistence.models.share import ExportJobModel, ImportJobModel


def _export_to_entity(model: ExportJobModel) -> ExportJob:
    return ExportJob(
        id=model.id,
        organization_id=model.organization_id,
        requested_by=model.requested_by,
        status=ExportJobStatus(model.status),
        export_format=ExportFormat(model.export_format),
        resource_ids=list(model.resource_ids or []),
        include_metadata=model.include_metadata,
        artifact_path=model.artifact_path,
        error_message=model.error_message,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _import_to_entity(model: ImportJobModel) -> ImportJob:
    return ImportJob(
        id=model.id,
        organization_id=model.organization_id,
        requested_by=model.requested_by,
        status=ImportJobStatus(model.status),
        source_path=model.source_path,
        target_folder_id=model.target_folder_id,
        items_processed=model.items_processed,
        items_failed=model.items_failed,
        error_message=model.error_message,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyExportJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: ExportJob) -> ExportJob:
        model = ExportJobModel(
            id=job.id,
            organization_id=job.organization_id,
            requested_by=job.requested_by,
            status=job.status.value,
            export_format=job.export_format.value,
            resource_ids=job.resource_ids,
            include_metadata=job.include_metadata,
            artifact_path=job.artifact_path,
            error_message=job.error_message,
            completed_at=job.completed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _export_to_entity(model)

    async def update(self, job: ExportJob) -> ExportJob:
        model = await self._session.get(ExportJobModel, job.id)
        if model is None:
            raise ValueError("Export job not found")
        model.status = job.status.value
        model.artifact_path = job.artifact_path
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        model.updated_at = job.updated_at
        await self._session.flush()
        return _export_to_entity(model)

    async def get_by_id(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> ExportJob | None:
        stmt = select(ExportJobModel).where(ExportJobModel.id == job_id)
        if organization_id.int != 0:
            stmt = stmt.where(ExportJobModel.organization_id == organization_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _export_to_entity(model) if model else None

    async def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 50
    ) -> Sequence[ExportJob]:
        stmt = (
            select(ExportJobModel)
            .where(ExportJobModel.organization_id == organization_id)
            .order_by(ExportJobModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_export_to_entity(m) for m in result.scalars().all()]


class SqlAlchemyImportJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: ImportJob) -> ImportJob:
        model = ImportJobModel(
            id=job.id,
            organization_id=job.organization_id,
            requested_by=job.requested_by,
            status=job.status.value,
            source_path=job.source_path,
            target_folder_id=job.target_folder_id,
            items_processed=job.items_processed,
            items_failed=job.items_failed,
            error_message=job.error_message,
            completed_at=job.completed_at,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _import_to_entity(model)

    async def update(self, job: ImportJob) -> ImportJob:
        model = await self._session.get(ImportJobModel, job.id)
        if model is None:
            raise ValueError("Import job not found")
        model.status = job.status.value
        model.items_processed = job.items_processed
        model.items_failed = job.items_failed
        model.error_message = job.error_message
        model.completed_at = job.completed_at
        model.updated_at = job.updated_at
        await self._session.flush()
        return _import_to_entity(model)

    async def get_by_id(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob | None:
        stmt = select(ImportJobModel).where(ImportJobModel.id == job_id)
        if organization_id.int != 0:
            stmt = stmt.where(ImportJobModel.organization_id == organization_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _import_to_entity(model) if model else None

    async def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 50
    ) -> Sequence[ImportJob]:
        stmt = (
            select(ImportJobModel)
            .where(ImportJobModel.organization_id == organization_id)
            .order_by(ImportJobModel.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [_import_to_entity(m) for m in result.scalars().all()]


class StubDocumentExportSource:
    async def fetch_documents(
        self,
        organization_id: uuid.UUID,
        resource_ids: list[uuid.UUID],
        *,
        include_metadata: bool,
        include_versions: bool,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": str(rid),
                "filename": f"{rid}.txt",
                "content": b"export stub content",
                "metadata": {"organization_id": str(organization_id)} if include_metadata else {},
            }
            for rid in resource_ids
        ]


class StubDocumentImportSink:
    async def import_document(
        self,
        organization_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
        metadata: dict[str, Any],
        target_folder_id: uuid.UUID | None,
        overwrite: bool,
    ) -> uuid.UUID:
        return uuid.uuid4()
