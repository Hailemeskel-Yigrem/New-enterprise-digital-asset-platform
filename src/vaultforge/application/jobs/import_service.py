"""Bulk import job application service."""

from __future__ import annotations

import json
import uuid
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.core.logging import get_logger
from vaultforge.domain.common import utc_now

log = get_logger(__name__)


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ImportJobCreateRequest(BaseModel):
    source_path: str = Field(min_length=1, max_length=1024)
    target_folder_id: uuid.UUID | None = None
    overwrite_existing: bool = False
    validate_checksums: bool = True


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    status: ImportJobStatus
    source_path: str
    target_folder_id: uuid.UUID | None
    items_processed: int
    items_failed: int
    error_message: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ImportJob:
    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by: uuid.UUID
    status: ImportJobStatus
    source_path: str
    target_folder_id: uuid.UUID | None = None
    overwrite_existing: bool = False
    validate_checksums: bool = True
    items_processed: int = 0
    items_failed: int = 0
    error_message: str | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


class ImportJobRepository(Protocol):
    async def add(self, job: ImportJob) -> ImportJob: ...
    async def update(self, job: ImportJob) -> ImportJob: ...
    async def get_by_id(
        self, organization_id: uuid.UUID, job_id: uuid.UUID
    ) -> ImportJob | None: ...
    async def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 50
    ) -> Sequence[ImportJob]: ...


class DocumentImportSink(Protocol):
    async def import_document(
        self,
        organization_id: uuid.UUID,
        *,
        filename: str,
        content: bytes,
        metadata: dict[str, Any],
        target_folder_id: uuid.UUID | None,
        overwrite: bool,
    ) -> uuid.UUID: ...


@dataclass(slots=True)
class ImportService:
    jobs: ImportJobRepository
    documents: DocumentImportSink

    async def create_import(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: ImportJobCreateRequest,
    ) -> ImportJobResponse:
        source = Path(payload.source_path)
        if not source.exists():
            raise ValidationError(f"Source path does not exist: {payload.source_path}")

        job = ImportJob(
            id=uuid.uuid4(),
            organization_id=organization_id,
            requested_by=actor_id,
            status=ImportJobStatus.PENDING,
            source_path=payload.source_path,
            target_folder_id=payload.target_folder_id,
            overwrite_existing=payload.overwrite_existing,
            validate_checksums=payload.validate_checksums,
        )
        saved = await self.jobs.add(job)
        log.info("import_job_created", job_id=str(saved.id), source=payload.source_path)
        return ImportJobResponse.model_validate(saved)

    async def get_job(
        self,
        organization_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> ImportJobResponse:
        job = await self._get_job(organization_id, job_id)
        return ImportJobResponse.model_validate(job)

    async def list_jobs(self, organization_id: uuid.UUID) -> list[ImportJobResponse]:
        jobs = await self.jobs.list_for_organization(organization_id)
        return [ImportJobResponse.model_validate(j) for j in jobs]

    async def run_import(self, job_id: uuid.UUID) -> ImportJobResponse:
        job = await self._get_job_any_org(job_id)
        job.status = ImportJobStatus.RUNNING
        job.updated_at = utc_now()
        await self.jobs.update(job)

        try:
            items = self._load_source(Path(job.source_path))
            processed = failed = 0
            errors: list[str] = []
            for item in items:
                try:
                    await self.documents.import_document(
                        job.organization_id,
                        filename=item["filename"],
                        content=item["content"],
                        metadata=item.get("metadata", {}),
                        target_folder_id=job.target_folder_id,
                        overwrite=job.overwrite_existing,
                    )
                    processed += 1
                except Exception as exc:
                    failed += 1
                    errors.append(f"{item.get('filename', '?')}: {exc}")

            job.items_processed = processed
            job.items_failed = failed
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            if failed and processed:
                job.status = ImportJobStatus.PARTIAL
                job.error_message = "; ".join(errors[:10])
            elif failed:
                job.status = ImportJobStatus.FAILED
                job.error_message = "; ".join(errors[:10])
            else:
                job.status = ImportJobStatus.COMPLETED
            saved = await self.jobs.update(job)
            log.info(
                "import_job_finished",
                job_id=str(job_id),
                processed=processed,
                failed=failed,
            )
            return ImportJobResponse.model_validate(saved)
        except Exception as exc:
            job.status = ImportJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            await self.jobs.update(job)
            raise

    def _load_source(self, source: Path) -> list[dict[str, Any]]:
        if source.suffix.lower() == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return self._normalize_items(data)
            if isinstance(data, dict) and "documents" in data:
                return self._normalize_items(data["documents"])
            raise ValidationError("Unsupported JSON import format")

        if source.suffix.lower() == ".zip":
            items: list[dict[str, Any]] = []
            with zipfile.ZipFile(source, "r") as archive:
                if "manifest.json" in archive.namelist():
                    manifest = json.loads(archive.read("manifest.json"))
                    meta_by_name = {d.get("filename", ""): d for d in manifest}
                else:
                    meta_by_name = {}
                for name in archive.namelist():
                    if name.endswith("/") or name == "manifest.json":
                        continue
                    filename = Path(name).name
                    meta = meta_by_name.get(filename, {})
                    items.append(
                        {
                            "filename": filename,
                            "content": archive.read(name),
                            "metadata": meta.get("metadata", meta),
                        }
                    )
            return items

        raise ValidationError(f"Unsupported import source: {source.suffix}")

    def _normalize_items(self, raw_items: list[Any]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            content = item.get("content", b"")
            if isinstance(content, str):
                content = content.encode("utf-8")
            normalized.append(
                {
                    "filename": item.get("filename", "imported.bin"),
                    "content": content,
                    "metadata": item.get("metadata", {}),
                }
            )
        return normalized

    async def _get_job(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob:
        job = await self.jobs.get_by_id(organization_id, job_id)
        if job is None:
            raise NotFoundError("Import job not found")
        return job

    async def _get_job_any_org(self, job_id: uuid.UUID) -> ImportJob:
        job = await self.jobs.get_by_id(uuid.UUID(int=0), job_id)
        if job is not None:
            return job
        raise NotFoundError("Import job not found")
