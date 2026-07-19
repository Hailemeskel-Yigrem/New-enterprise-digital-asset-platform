"""Unit tests for metadata application service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.assets.metadata_schemas import (
    MetadataFieldDefinitionRequest,
    MetadataSchemaCreateRequest,
    MetadataValueUpsertRequest,
)
from vaultforge.application.assets.metadata_service import MetadataService
from vaultforge.core.exceptions import ConflictError, NotFoundError
from vaultforge.domain.assets.metadata import MetadataFieldType, MetadataSchema


@pytest.fixture
def org_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def schema_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_by_slug = AsyncMock(return_value=None)
    repo.add = AsyncMock(side_effect=lambda s: s)
    repo.get_by_id = AsyncMock()
    repo.update = AsyncMock(side_effect=lambda s: s)
    repo.list_for_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def value_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_for_resource = AsyncMock(return_value=None)
    repo.upsert = AsyncMock(side_effect=lambda v: v)
    return repo


@pytest.fixture
def service(schema_repo: AsyncMock, value_repo: AsyncMock) -> MetadataService:
    return MetadataService(schema_repo, value_repo)


@pytest.mark.asyncio
async def test_create_schema(
    service: MetadataService, org_id: uuid.UUID, schema_repo: AsyncMock
) -> None:
    payload = MetadataSchemaCreateRequest(
        name="Contract",
        slug="contract",
        fields=[
            MetadataFieldDefinitionRequest(
                key="counterparty",
                label="Counterparty",
                field_type=MetadataFieldType.STRING,
            ),
        ],
    )
    result = await service.create_schema(org_id, uuid.uuid4(), payload)
    assert result.slug == "contract"
    schema_repo.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_schema_conflict(
    service: MetadataService, org_id: uuid.UUID, schema_repo: AsyncMock
) -> None:
    schema_repo.get_by_slug = AsyncMock(return_value=MetadataSchema(name="X", slug="contract"))
    payload = MetadataSchemaCreateRequest(name="X", slug="contract", fields=[])
    with pytest.raises(ConflictError):
        await service.create_schema(org_id, uuid.uuid4(), payload)


@pytest.mark.asyncio
async def test_upsert_values(
    service: MetadataService, org_id: uuid.UUID, schema_repo: AsyncMock
) -> None:
    schema = MetadataSchema(
        organization_id=org_id,
        name="S",
        slug="s",
        fields=[],
    )
    schema_repo.get_by_id = AsyncMock(return_value=schema)
    result = await service.upsert_values(
        org_id,
        schema.id,
        "document",
        uuid.uuid4(),
        uuid.uuid4(),
        MetadataValueUpsertRequest(values={}),
    )
    assert result.schema_id == schema.id


@pytest.mark.asyncio
async def test_update_schema_not_found(
    service: MetadataService, org_id: uuid.UUID, schema_repo: AsyncMock
) -> None:
    schema_repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundError):
        await service.update_schema(
            org_id, uuid.uuid4(), MetadataSchemaCreateRequest(name="X", slug="x", fields=[])
        )
