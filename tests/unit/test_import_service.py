"""Unit tests for ImportService."""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence

import pytest

from vaultforge.application.jobs.import_service import (
    ImportJob,
    ImportJobCreateRequest,
    ImportJobStatus,
    ImportService,
)
from vaultforge.core.exceptions import NotFoundError, ValidationError


class MemoryImportJobs:
    def __init__(self) -> None:
        self.items: list[ImportJob] = []

    async def add(self, job: ImportJob) -> ImportJob:
        self.items.append(job)
        return job

    async def update(self, job: ImportJob) -> ImportJob:
        return job

    async def get_by_id(self, organization_id: uuid.UUID, job_id: uuid.UUID) -> ImportJob | None:
        return next((j for j in self.items if j.id == job_id), None)

    async def list_for_organization(
        self, organization_id: uuid.UUID, *, limit: int = 50
    ) -> Sequence[ImportJob]:
        return self.items


class StubSink:
    async def import_document(
        self, organization_id, *, filename, content, metadata, target_folder_id, overwrite
    ):
        return uuid.uuid4()


@pytest.fixture
def import_service() -> ImportService:
    return ImportService(MemoryImportJobs(), StubSink())


@pytest.mark.asyncio
async def test_create_import_missing_source(import_service: ImportService) -> None:
    with pytest.raises(ValidationError):
        await import_service.create_import(
            uuid.uuid4(),
            uuid.uuid4(),
            ImportJobCreateRequest(source_path="/nonexistent/path.json"),
        )


@pytest.mark.asyncio
async def test_run_import_json(import_service: ImportService, tmp_path) -> None:
    source = tmp_path / "import.json"
    source.write_text(
        json.dumps([{"filename": "a.txt", "content": "hello", "metadata": {}}]),
        encoding="utf-8",
    )
    org_id = uuid.uuid4()
    actor = uuid.uuid4()
    job = await import_service.create_import(
        org_id,
        actor,
        ImportJobCreateRequest(source_path=str(source)),
    )
    result = await import_service.run_import(job.id)
    assert result.status == ImportJobStatus.COMPLETED
    assert result.items_processed == 1


@pytest.mark.asyncio
async def test_get_missing_import_job(import_service: ImportService) -> None:
    with pytest.raises(NotFoundError):
        await import_service.get_job(uuid.uuid4(), uuid.uuid4())


def test_load_unsupported_source(import_service: ImportService, tmp_path) -> None:
    bad = tmp_path / "file.xyz"
    bad.write_text("data", encoding="utf-8")
    with pytest.raises(ValidationError):
        import_service._load_source(bad)
