"""SQLAlchemy metadata repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.domain.assets.metadata import (
    MetadataFieldDefinition,
    MetadataQueryFilter,
    MetadataSchema,
    MetadataValue,
)
from vaultforge.domain.assets.metadata_repositories import (
    MetadataSchemaRepository,
    MetadataValueRepository,
)
from vaultforge.infrastructure.persistence.models.metadata import (
    MetadataSchemaModel,
    MetadataValueModel,
)


def _schema_from_model(model: MetadataSchemaModel) -> MetadataSchema:
    fields = [
        MetadataFieldDefinition(
            key=f["key"],
            label=f["label"],
            field_type=f["field_type"],
            required=f.get("required", False),
            description=f.get("description", ""),
            default_value=f.get("default_value"),
            enum_options=tuple(f.get("enum_options", [])),
            searchable=f.get("searchable", True),
            sort_order=f.get("sort_order", 0),
        )
        for f in model.fields_json
    ]
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


def _schema_to_fields_json(schema: MetadataSchema) -> list[dict[str, Any]]:
    return [
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
    ]


def _value_from_model(model: MetadataValueModel) -> MetadataValue:
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


class SqlAlchemyMetadataSchemaRepository(MetadataSchemaRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, organization_id: uuid.UUID, schema_id: uuid.UUID
    ) -> MetadataSchema | None:
        stmt = select(MetadataSchemaModel).where(
            MetadataSchemaModel.organization_id == organization_id,
            MetadataSchemaModel.id == schema_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _schema_from_model(model) if model else None

    async def get_by_slug(self, organization_id: uuid.UUID, slug: str) -> MetadataSchema | None:
        stmt = select(MetadataSchemaModel).where(
            MetadataSchemaModel.organization_id == organization_id,
            MetadataSchemaModel.slug == slug,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _schema_from_model(model) if model else None

    async def add(self, schema: MetadataSchema) -> MetadataSchema:
        model = MetadataSchemaModel(
            id=schema.id,
            organization_id=schema.organization_id,
            name=schema.name,
            slug=schema.slug,
            description=schema.description,
            resource_type=schema.resource_type,
            version=schema.version,
            is_active=schema.is_active,
            fields_json=_schema_to_fields_json(schema),
            created_by=schema.created_by,
            created_at=schema.created_at,
            updated_at=schema.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return schema

    async def update(self, schema: MetadataSchema) -> MetadataSchema:
        model = await self._session.get(MetadataSchemaModel, schema.id)
        if model is None:
            raise ValueError("Schema model not found")
        model.name = schema.name
        model.description = schema.description
        model.version = schema.version
        model.is_active = schema.is_active
        model.fields_json = _schema_to_fields_json(schema)
        model.updated_at = schema.updated_at
        await self._session.flush()
        return schema

    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        resource_type: str | None = None,
        active_only: bool = True,
    ) -> Sequence[MetadataSchema]:
        stmt = select(MetadataSchemaModel).where(
            MetadataSchemaModel.organization_id == organization_id
        )
        if resource_type is not None:
            stmt = stmt.where(MetadataSchemaModel.resource_type == resource_type)
        if active_only:
            stmt = stmt.where(MetadataSchemaModel.is_active.is_(True))
        result = await self._session.execute(stmt)
        return [_schema_from_model(m) for m in result.scalars()]


class SqlAlchemyMetadataValueRepository(MetadataValueRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        *,
        schema_id: uuid.UUID | None = None,
    ) -> MetadataValue | None:
        stmt = select(MetadataValueModel).where(
            MetadataValueModel.organization_id == organization_id,
            MetadataValueModel.resource_type == resource_type,
            MetadataValueModel.resource_id == resource_id,
        )
        if schema_id is not None:
            stmt = stmt.where(MetadataValueModel.schema_id == schema_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _value_from_model(model) if model else None

    async def upsert(self, value: MetadataValue) -> MetadataValue:
        model = await self._session.get(MetadataValueModel, value.id)
        if model is None:
            model = MetadataValueModel(
                id=value.id,
                organization_id=value.organization_id,
                schema_id=value.schema_id,
                schema_version=value.schema_version,
                resource_type=value.resource_type,
                resource_id=value.resource_id,
                values_json=value.values,
                updated_by=value.updated_by,
                created_at=value.created_at,
                updated_at=value.updated_at,
            )
            self._session.add(model)
        else:
            model.schema_version = value.schema_version
            model.values_json = value.values
            model.updated_by = value.updated_by
            model.updated_at = value.updated_at
        await self._session.flush()
        return value

    async def delete_for_resource(
        self, organization_id: uuid.UUID, resource_type: str, resource_id: uuid.UUID
    ) -> None:
        stmt = delete(MetadataValueModel).where(
            MetadataValueModel.organization_id == organization_id,
            MetadataValueModel.resource_type == resource_type,
            MetadataValueModel.resource_id == resource_id,
        )
        await self._session.execute(stmt)

    async def search(self, query: MetadataQueryFilter) -> Sequence[MetadataValue]:
        stmt = select(MetadataValueModel).where(
            MetadataValueModel.organization_id == query.organization_id
        )
        if query.schema_id is not None:
            stmt = stmt.where(MetadataValueModel.schema_id == query.schema_id)
        if query.resource_type is not None:
            stmt = stmt.where(MetadataValueModel.resource_type == query.resource_type)
        if query.resource_ids:
            stmt = stmt.where(MetadataValueModel.resource_id.in_(query.resource_ids))
        stmt = stmt.limit(query.limit).offset(query.offset)
        result = await self._session.execute(stmt)
        return [_value_from_model(m) for m in result.scalars()]

    async def bulk_delete_for_resources(
        self, organization_id: uuid.UUID, resource_type: str, resource_ids: list[uuid.UUID]
    ) -> int:
        if not resource_ids:
            return 0
        stmt = delete(MetadataValueModel).where(
            MetadataValueModel.organization_id == organization_id,
            MetadataValueModel.resource_type == resource_type,
            MetadataValueModel.resource_id.in_(resource_ids),
        )
        result = await self._session.execute(stmt)
        return cast(CursorResult[Any], result).rowcount or 0
