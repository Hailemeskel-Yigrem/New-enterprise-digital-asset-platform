"""Unit tests for metadata domain entities."""

from __future__ import annotations

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.assets.metadata import (
    MetadataFieldDefinition,
    MetadataFieldType,
    MetadataSchema,
    MetadataValue,
)


def test_field_definition_validates_enum() -> None:
    defn = MetadataFieldDefinition(
        key="status",
        label="Status",
        field_type=MetadataFieldType.ENUM,
        enum_options=("draft", "published"),
    )
    assert defn.validate_value("draft") == "draft"
    with pytest.raises(ValidationError):
        defn.validate_value("invalid")


def test_field_definition_required() -> None:
    defn = MetadataFieldDefinition(
        key="title",
        label="Title",
        field_type=MetadataFieldType.STRING,
        required=True,
    )
    with pytest.raises(ValidationError):
        defn.validate_value(None)


def test_schema_rejects_duplicate_keys() -> None:
    fields = [
        MetadataFieldDefinition(key="field_a", label="A", field_type=MetadataFieldType.STRING),
        MetadataFieldDefinition(key="field_a", label="A2", field_type=MetadataFieldType.STRING),
    ]
    with pytest.raises(ValidationError):
        MetadataSchema(name="Test", slug="test", fields=fields)


def test_schema_validate_payload() -> None:
    schema = MetadataSchema(
        name="Doc Meta",
        slug="doc-meta",
        fields=[
            MetadataFieldDefinition(
                key="department", label="Dept", field_type=MetadataFieldType.STRING
            ),
        ],
    )
    result = schema.validate_payload({"department": " Legal "})
    assert result["department"] == "Legal"


def test_schema_rejects_unknown_fields() -> None:
    schema = MetadataSchema(name="S", slug="s", fields=[])
    with pytest.raises(ValidationError):
        schema.validate_payload({"unknown": "x"})


def test_metadata_value_merge() -> None:
    schema = MetadataSchema(
        name="S",
        slug="s",
        fields=[
            MetadataFieldDefinition(key="field_a", label="A", field_type=MetadataFieldType.STRING),
            MetadataFieldDefinition(key="field_b", label="B", field_type=MetadataFieldType.INTEGER),
        ],
    )
    value = MetadataValue(values={"field_a": "hello"})
    value.merge({"field_b": 42}, schema)
    assert value.values == {"field_a": "hello", "field_b": 42}


def test_schema_apply_defaults() -> None:
    schema = MetadataSchema(
        name="S",
        slug="s",
        fields=[
            MetadataFieldDefinition(
                key="priority",
                label="Priority",
                field_type=MetadataFieldType.INTEGER,
                default_value=1,
            ),
        ],
    )
    merged = schema.apply_defaults({})
    assert merged["priority"] == 1
