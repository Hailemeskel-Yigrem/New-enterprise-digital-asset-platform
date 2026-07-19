"""Custom metadata schema and value application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from vaultforge.application.assets.metadata_schemas import (
    MetadataFieldDefinitionRequest,
    MetadataSchemaCreateRequest,
    MetadataSchemaResponse,
    MetadataSchemaUpdateRequest,
    MetadataValueResponse,
    MetadataValueUpsertRequest,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError
from vaultforge.domain.assets.metadata import MetadataFieldDefinition, MetadataSchema, MetadataValue
from vaultforge.domain.assets.metadata_repositories import (
    MetadataSchemaRepository,
    MetadataValueRepository,
)


def _to_field(defn: MetadataFieldDefinitionRequest) -> MetadataFieldDefinition:
    return MetadataFieldDefinition(
        key=defn.key,
        label=defn.label,
        field_type=defn.field_type,
        required=defn.required,
        description=defn.description,
        default_value=defn.default_value,
        enum_options=tuple(defn.enum_options),
        searchable=defn.searchable,
        sort_order=defn.sort_order,
    )


@dataclass(slots=True)
class MetadataService:
    schemas: MetadataSchemaRepository
    values: MetadataValueRepository

    async def create_schema(
        self,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: MetadataSchemaCreateRequest,
    ) -> MetadataSchemaResponse:
        existing = await self.schemas.get_by_slug(organization_id, payload.slug)
        if existing is not None:
            raise ConflictError("Schema slug already exists")
        schema = MetadataSchema(
            organization_id=organization_id,
            name=payload.name,
            slug=payload.slug,
            description=payload.description,
            resource_type=payload.resource_type,
            fields=[_to_field(f) for f in payload.fields],
            created_by=actor_id,
        )
        saved = await self.schemas.add(schema)
        return MetadataSchemaResponse.model_validate(_schema_to_dict(saved))

    async def update_schema(
        self,
        organization_id: uuid.UUID,
        schema_id: uuid.UUID,
        payload: MetadataSchemaUpdateRequest,
    ) -> MetadataSchemaResponse:
        schema = await self._require_schema(organization_id, schema_id)
        if payload.name is not None:
            schema.name = payload.name
        if payload.description is not None:
            schema.description = payload.description
        if payload.fields is not None:
            schema.fields = [_to_field(f) for f in payload.fields]
            schema.bump_version()
        else:
            schema.touch()
        saved = await self.schemas.update(schema)
        return MetadataSchemaResponse.model_validate(_schema_to_dict(saved))

    async def list_schemas(self, organization_id: uuid.UUID) -> list[MetadataSchemaResponse]:
        schemas = await self.schemas.list_for_organization(organization_id)
        return [MetadataSchemaResponse.model_validate(_schema_to_dict(s)) for s in schemas]

    async def deactivate_schema(
        self, organization_id: uuid.UUID, schema_id: uuid.UUID
    ) -> MetadataSchemaResponse:
        schema = await self._require_schema(organization_id, schema_id)
        schema.deactivate()
        saved = await self.schemas.update(schema)
        return MetadataSchemaResponse.model_validate(_schema_to_dict(saved))

    async def upsert_values(
        self,
        organization_id: uuid.UUID,
        schema_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        actor_id: uuid.UUID,
        payload: MetadataValueUpsertRequest,
    ) -> MetadataValueResponse:
        schema = await self._require_schema(organization_id, schema_id)
        existing = await self.values.get_for_resource(
            organization_id, resource_type, resource_id, schema_id=schema_id
        )
        if existing is None:
            value = MetadataValue(
                organization_id=organization_id,
                schema_id=schema_id,
                resource_type=resource_type,
                resource_id=resource_id,
                updated_by=actor_id,
            )
            value.replace(payload.values, schema)
            saved = await self.values.upsert(value)
        else:
            existing.updated_by = actor_id
            existing.replace(payload.values, schema)
            saved = await self.values.upsert(existing)
        return MetadataValueResponse.model_validate(saved)

    async def get_values(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> MetadataValueResponse | None:
        value = await self.values.get_for_resource(organization_id, resource_type, resource_id)
        if value is None:
            return None
        return MetadataValueResponse.model_validate(value)

    async def _require_schema(
        self, organization_id: uuid.UUID, schema_id: uuid.UUID
    ) -> MetadataSchema:
        schema = await self.schemas.get_by_id(organization_id, schema_id)
        if schema is None:
            raise NotFoundError("Metadata schema not found")
        return schema


def _schema_to_dict(schema: MetadataSchema) -> dict[str, Any]:
    return {
        "id": schema.id,
        "organization_id": schema.organization_id,
        "name": schema.name,
        "slug": schema.slug,
        "description": schema.description,
        "resource_type": schema.resource_type,
        "version": schema.version,
        "is_active": schema.is_active,
        "fields": [
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
        "created_by": schema.created_by,
        "created_at": schema.created_at,
        "updated_at": schema.updated_at,
    }
