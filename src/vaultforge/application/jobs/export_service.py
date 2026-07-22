"""Bulk export job application service."""

from __future__ import annotations

import json
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from vaultforge.core.config import get_settings
from vaultforge.core.exceptions import ConflictError, NotFoundError, ValidationError
from vaultforge.core.logging import get_logger
from vaultforge.domain.common import utc_now

log = get_logger(__name__)


class ExportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExportFormat(StrEnum):
    ZIP = "zip"
    JSON = "json"
    MANIFEST = "manifest"


class ExportJobCreateRequest(BaseModel):
    resource_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)
    export_format: ExportFormat = ExportFormat.ZIP
    include_metadata: bool = True
    include_versions: bool = False
    password: str | None = Field(default=None, min_length=8, max_length=128)


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    status: ExportJobStatus
    export_format: ExportFormat
    resource_ids: list[uuid.UUID]
    include_metadata: bool
    artifact_path: str | None
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ExportJob:
    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    status: ExportJobStatus
    export_format: ExportFormat
    resource_ids: list[uuid.UUID]
    include_metadata: bool
    include_versions: bool = False
    artifact_path: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


class ExportJobRepository(Protocol):
    async def add(self, job: ExportJob) -> ExportJob: ...
    async def update(self, job: ExportJob) -> ExportJob: ...
    async def get_by_id(
        self, organization_id: uuid.UUID, job_id: uuid.UUID
    ) -> ExportJob | None: ...
    async def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 50
    ) -> Sequence[ExportJob]: ...


class DocumentExportSource(Protocol):
    async def fetch_documents(
        self,
        organization_id: uuid.UUID,
        resource_ids: list[uuid.UUID],
        *,
        include_metadata: bool,
        include_versions: bool,
    ) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class ExportService:
    jobs: ExportJobRepository
    documents: DocumentExportSource

    async def create_export(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ExportJobCreateRequest,
    ) -> ExportJobResponse:
        active = await self.jobs.list_for_organization(organization_id, limit=20)
        running = [
            j for j in active if j.status in {ExportJobStatus.PENDING, ExportJobStatus.RUNNING}
        ]
        if len(running) >= 5:
            raise ConflictError("Too many active export jobs for this organization")

        job = ExportJob(
            id=uuid.uuid4(),
            organization_id=organization_id,
            requested_by=actor_id,
            status=ExportJobStatus.PENDING,
            export_format=payload.export_format,
            resource_ids=list(payload.resource_ids),
            include_metadata=payload.include_metadata,
            include_versions=payload.include_versions,
        )
        saved = await self.jobs.add(job)
        log.info("export_job_created", job_id=str(saved.id), resource_count=len(saved.resource_ids))
        return ExportJobResponse.model_validate(saved)

    async def get_job(
        self,
        organization_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ExportJobResponse:
        job = await self._get_job(organization_id, job_id)
        return ExportJobResponse.model_validate(job)

    async def list_jobs(self, organization_id: uuid.UUID) -> list[ExportJobResponse]:
        jobs = await self.jobs.list_for_organization(organization_id)
        return [ExportJobResponse.model_validate(j) for j in jobs]

    async def cancel_job(
        self,
        organization_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ExportJobResponse:
        job = await self._get_job(organization_id, job_id)
        if job.status in {ExportJobStatus.COMPLETED, ExportJobStatus.FAILED}:
            raise ValidationError("Cannot cancel a finished job")
        job.status = ExportJobStatus.CANCELLED
        job.updated_at = utc_now()
        saved = await self.jobs.update(job)
        return ExportJobResponse.model_validate(saved)

    async def run_export(self, job_id: uuid.UUID) -> ExportJobResponse:
        """Execute export synchronously (called from Celery worker)."""
        job = await self._get_job_by_id(job_id)
        if job.status == ExportJobStatus.CANCELLED:
            raise ValidationError("Export job was cancelled")
        job.status = ExportJobStatus.RUNNING
        job.updated_at = utc_now()
        await self.jobs.update(job)

        try:
            documents = await self.documents.fetch_documents(
                job.organization_id,
                job.resource_ids,
                include_metadata=job.include_metadata,
                include_versions=job.include_versions,
            )
            artifact_path = self._write_artifact(job, documents)
            job.status = ExportJobStatus.COMPLETED
            job.artifact_path = artifact_path
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            saved = await self.jobs.update(job)
            log.info("export_job_completed", job_id=str(job_id), artifact=artifact_path)
            return ExportJobResponse.model_validate(saved)
        except Exception as exc:
            job.status = ExportJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            await self.jobs.update(job)
            log.error("export_job_failed", job_id=str(job_id), error=str(exc))
            raise

    def _write_artifact(self, job: ExportJob, documents: list[dict[str, Any]]) -> str:
        settings = get_settings()
        export_dir = Path(settings.storage_local_path) / "exports" / str(job.organization_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = utc_now().strftime("%Y%m%dT%H%M%S")
        if job.export_format == ExportFormat.JSON:
            path = export_dir / f"export_{job.id}_{timestamp}.json"
            path.write_text(json.dumps(documents, indent=2, default=str), encoding="utf-8")
            return str(path)
        if job.export_format == ExportFormat.MANIFEST:
            manifest = {
                "job_id": str(job.id),
                "organization_id": str(job.organization_id),
                "document_count": len(documents),
                "documents": documents,
            }
            path = export_dir / f"manifest_{job.id}_{timestamp}.json"
            path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
            return str(path)

        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(documents, indent=2, default=str))
            for index, doc in enumerate(documents):
                name = doc.get("filename", f"document_{index}.bin")
                content = doc.get("content", b"")
                if isinstance(content, str):
                    content = content.encode("utf-8")
                archive.writestr(f"files/{name}", content)
        path = export_dir / f"export_{job.id}_{timestamp}.zip"
        path.write_bytes(buffer.getvalue())
        return str(path)

    async def _get_job(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> ExportJob:
        job = await self.jobs.get_by_id(organization_id, job_id)
        if job is None:
            raise NotFoundError("Export job not found")
        return job

    async def _get_job_by_id(self, job_id: uuid.UUID) -> ExportJob:
        org_placeholder = uuid.UUID(int=0)
        job = await self.jobs.get_by_id(org_placeholder, job_id)
        if job is not None:
            return job
        raise NotFoundError("Export job not found")
