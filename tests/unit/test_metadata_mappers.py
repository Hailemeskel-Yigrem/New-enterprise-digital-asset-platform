"""Unit tests for metadata mappers."""

from __future__ import annotations

import uuid

from vaultforge.domain.assets.metadata import (
    MetadataFieldDefinition,
    MetadataFieldType,
    MetadataSchema,
)
from vaultforge.infrastructure.persistence.mappers.metadata import field_to_dict, schema_from_model
from vaultforge.infrastructure.persistence.models.metadata import MetadataSchemaModel


def test_field_roundtrip_dict() -> None:
    field = MetadataFieldDefinition(
        key="department",
        label="Department",
        field_type=MetadataFieldType.STRING,
        required=True,
    )
    restored = field_to_dict(field)
    assert restored["key"] == "department"
    assert restored["required"] is True


def test_schema_from_model() -> None:
    model = MetadataSchemaModel(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        name="Test",
        slug="test",
        fields_json=[{"key": "dept", "label": "Dept", "field_type": "string"}],
        created_by=uuid.uuid4(),
    )
    schema = schema_from_model(model)
    assert isinstance(schema, MetadataSchema)
    assert schema.fields[0].key == "dept"
