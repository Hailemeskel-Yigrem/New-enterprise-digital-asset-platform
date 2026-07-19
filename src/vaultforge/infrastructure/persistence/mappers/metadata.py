"""Mappers between metadata ORM models and domain entities."""

from __future__ import annotations

from typing import Any

from vaultforge.domain.assets.metadata import MetadataFieldDefinition, MetadataSchema, MetadataValue
from vaultforge.infrastructure.persistence.models.metadata import (
    MetadataSchemaModel,
    MetadataValueModel,
)


def field_from_dict(data: dict[str, Any]) -> MetadataFieldDefinition:
    return MetadataFieldDefinition(
        key=data["key"],
        label=data["label"],
        field_type=data["field_type"],
        required=data.get("required", False),
        description=data.get("description", ""),
        default_value=data.get("default_value"),
        enum_options=tuple(data.get("enum_options", [])),
        min_value=data.get("min_value"),
        max_value=data.get("max_value"),
        min_length=data.get("min_length"),
        max_length=data.get("max_length"),
        searchable=data.get("searchable", True),
        sort_order=data.get("sort_order", 0),
    )


def field_to_dict(field: MetadataFieldDefinition) -> dict[str, Any]:
    return {
        "key": field.key,
        "label": field.label,
        "field_type": field.field_type,
        "required": field.required,
        "description": field.description,
        "default_value": field.default_value,
        "enum_options": list(field.enum_options),
        "min_value": field.min_value,
        "max_value": field.max_value,
        "min_length": field.min_length,
        "max_length": field.max_length,
        "searchable": field.searchable,
        "sort_order": field.sort_order,
    }


def schema_from_model(model: MetadataSchemaModel) -> MetadataSchema:
    fields = [field_from_dict(item) for item in model.fields_json]
    return MetadataSchema(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        slug=model.slug,
        description=model.description,
        resource_type=model.resource_type,
        version=model.version,
        is_active=model.is_active,
        fields=fields,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_schema_to_model(model: MetadataSchemaModel, schema: MetadataSchema) -> None:
    model.name = schema.name
    model.slug = schema.slug
    model.description = schema.description
    model.resource_type = schema.resource_type
    model.version = schema.version
    model.is_active = schema.is_active
    model.fields_json = [field_to_dict(f) for f in schema.fields]
    model.updated_at = schema.updated_at


def value_from_model(model: MetadataValueModel) -> MetadataValue:
    return MetadataValue(
        id=model.id,
        organization_id=model.organization_id,
        schema_id=model.schema_id,
        schema_version=model.schema_version,
        resource_type=model.resource_type,
        resource_id=model.resource_id,
        values=dict(model.values_json),
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def apply_value_to_model(model: MetadataValueModel, value: MetadataValue) -> None:
    model.schema_version = value.schema_version
    model.values_json = value.values
    model.updated_by = value.updated_by
    model.updated_at = value.updated_at
