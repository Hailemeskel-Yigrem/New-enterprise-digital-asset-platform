"""Unit tests for ExportService."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import pytest

from vaultforge.application.jobs.export_service import (
    ExportFormat,
    ExportJob,
    ExportJobCreateRequest,
    ExportJobStatus,
    ExportService,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError


class MemoryExportJobs:
    def __init__(self) -> None:
        self.items: list[ExportJob] = []

    async def add(self, job: ExportJob) -> ExportJob:
        self.items.append(job)
        return job

    async def update(self, job: ExportJob) -> ExportJob:
        return job

    async def get_by_id(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> ExportJob | None:
        return next((j for j in self.items if j.id == job_id), None)

    async def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 50
    ) -> Sequence[ExportJob]:
        return self.items


class StubDocs:
    async def fetch_documents(
        self, organization_id, resource_ids, *, include_metadata, include_versions
    ):
        return [
            {"filename": f"{rid}.txt", "content": b"data", "metadata": {"id": str(rid)}}
            for rid in resource_ids
        ]


@pytest.fixture
def export_service() -> ExportService:
    return ExportService(MemoryExportJobs(), StubDocs())


@pytest.mark.asyncio
async def test_create_export_job(export_service: ExportService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    resource_ids = [uuid.uuid4(), uuid.uuid4()]
    result = await export_service.create_export(
        org_id,
        actor,
        ExportJobCreateRequest(resource_ids=resource_ids, export_format=ExportFormat.JSON),
    )
    assert result.status == ExportJobStatus.PENDING
    assert len(result.resource_ids) == 2


@pytest.mark.asyncio
async def test_run_export_json(export_service: ExportService, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_PATH", str(tmp_path))
    from vaultforge.core.config import get_settings

    get_settings.cache_clear()

    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    job = await export_service.create_export(
        org_id,
        actor,
        ExportJobCreateRequest(resource_ids=[uuid.uuid4()], export_format=ExportFormat.JSON),
    )
    result = await export_service.run_export(job.id)
    assert result.status == ExportJobStatus.COMPLETED
    assert result.artifact_path is not None


@pytest.mark.asyncio
async def test_get_missing_job(export_service: ExportService) -> None:
    with pytest.raises(NotFoundError):
        await export_service.get_job(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_too_many_active_jobs(export_service: ExportService) -> None:
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    repo = export_service.jobs
    for _ in range(5):
        await repo.add(
            ExportJob(
                id=uuid.uuid4(),
                organization_id=org_id,
                requested_by=actor,
                status=ExportJobStatus.PENDING,
                export_format=ExportFormat.ZIP,
                resource_ids=[uuid.uuid4()],
                include_metadata=True,
            )
        )
    with pytest.raises(ConflictError):
        await export_service.create_export(
            org_id,
            actor,
            ExportJobCreateRequest(resource_ids=[uuid.uuid4()]),
        )
