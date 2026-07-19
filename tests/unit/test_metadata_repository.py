"""Unit tests for metadata SQLAlchemy repositories using a mocked session."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from vaultforge.domain.assets.metadata import (
    MetadataFieldDefinition,
    MetadataFieldType,
    MetadataSchema,
    MetadataValue,
)
from vaultforge.infrastructure.persistence.models.metadata import (
    MetadataSchemaModel,
    MetadataValueModel,
)
from vaultforge.infrastructure.persistence.repositories.metadata_repository import (
    SqlAlchemyMetadataSchemaRepository,
    SqlAlchemyMetadataValueRepository,
)


def _schema_model_from(schema: MetadataSchema) -> MetadataSchemaModel:
    return MetadataSchemaModel(
        id=schema.id,
        organization_id=schema.organization_id,
        name=schema.name,
        slug=schema.slug,
        description=schema.description,
        resource_type=schema.resource_type,
        version=schema.version,
        is_active=schema.is_active,
        fields_json=[
            {
                "key": f.key,
                "label": f.label,
                "field_type": f.field_type,
                "required": f.required,
                "description": f.description,
                "default_value": f.default_value,
                "enum_options": list(f.enum_options),
                "searchable": f.searchable,
                "sort_order": f.sort_order,
            }
            for f in schema.fields
        ],
        created_by=schema.created_by,
        created_at=schema.created_at,
        updated_at=schema.updated_at,
    )


async def test_schema_repository_add_flushes_and_returns_entity() -> None:
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    repo = SqlAlchemyMetadataSchemaRepository(session)

    org_id = uuid.uuid4()
    schema = MetadataSchema(
        organization_id=org_id,
        name="Test",
        slug="test",
        fields=[
            MetadataFieldDefinition(key="field_a", label="F", field_type=MetadataFieldType.STRING)
        ],
    )

    result = await repo.add(schema)

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert result is schema


async def test_schema_repository_get_by_slug_maps_model_to_entity() -> None:
    org_id = uuid.uuid4()
    schema = MetadataSchema(
        organization_id=org_id,
        name="Test",
        slug="test",
        fields=[
            MetadataFieldDefinition(key="field_a", label="F", field_type=MetadataFieldType.STRING)
        ],
    )
    model = _schema_model_from(schema)

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = model
    session.execute = AsyncMock(return_value=execute_result)
    repo = SqlAlchemyMetadataSchemaRepository(session)

    loaded = await repo.get_by_slug(org_id, "test")

    assert loaded is not None
    assert loaded.name == "Test"
    assert loaded.slug == "test"
    assert len(loaded.fields) == 1
    assert loaded.fields[0].key == "field_a"


async def test_schema_repository_get_by_slug_returns_none_when_missing() -> None:
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=execute_result)
    repo = SqlAlchemyMetadataSchemaRepository(session)

    loaded = await repo.get_by_slug(uuid.uuid4(), "missing")

    assert loaded is None


async def test_value_repository_upsert_inserts_new_value_when_absent() -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()
    session.flush = AsyncMock()
    repo = SqlAlchemyMetadataValueRepository(session)

    org_id = uuid.uuid4()
    value = MetadataValue(
        organization_id=org_id,
        resource_type="document",
        resource_id=uuid.uuid4(),
        values={"a": "b"},
    )

    result = await repo.upsert(value)

    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    assert result is value
    assert result.values["a"] == "b"


async def test_value_repository_upsert_updates_existing_model() -> None:
    org_id = uuid.uuid4()
    value = MetadataValue(
        organization_id=org_id,
        resource_type="document",
        resource_id=uuid.uuid4(),
        values={"a": "b"},
    )
    existing_model = MetadataValueModel(
        id=value.id,
        organization_id=org_id,
        schema_id=value.schema_id,
        schema_version=1,
        resource_type="document",
        resource_id=value.resource_id,
        values_json={"a": "old"},
        updated_by=value.updated_by,
        created_at=value.created_at,
        updated_at=value.updated_at,
    )

    session = AsyncMock()
    session.get = AsyncMock(return_value=existing_model)
    session.flush = AsyncMock()
    repo = SqlAlchemyMetadataValueRepository(session)

    value.values = {"a": "new"}
    await repo.upsert(value)

    assert existing_model.values_json == {"a": "new"}
    session.flush.assert_awaited_once()


async def test_value_repository_get_for_resource_maps_model() -> None:
    org_id = uuid.uuid4()
    resource_id = uuid.uuid4()
    model = MetadataValueModel(
        id=uuid.uuid4(),
        organization_id=org_id,
        schema_id=uuid.uuid4(),
        schema_version=1,
        resource_type="document",
        resource_id=resource_id,
        values_json={"a": "b"},
        updated_by=uuid.uuid4(),
    )
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = model
    session.execute = AsyncMock(return_value=execute_result)
    repo = SqlAlchemyMetadataValueRepository(session)

    loaded = await repo.get_for_resource(org_id, "document", resource_id)

    assert loaded is not None
    assert loaded.values["a"] == "b"


async def test_value_repository_bulk_delete_returns_zero_for_empty_list() -> None:
    session = AsyncMock()
    repo = SqlAlchemyMetadataValueRepository(session)

    deleted = await repo.bulk_delete_for_resources(uuid.uuid4(), "document", [])

    assert deleted == 0
    session.execute.assert_not_awaited()
