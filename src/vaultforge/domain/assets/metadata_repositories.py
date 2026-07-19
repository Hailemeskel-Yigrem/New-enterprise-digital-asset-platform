"""Repository interfaces for custom metadata."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence

from vaultforge.domain.assets.metadata import MetadataQueryFilter, MetadataSchema, MetadataValue


class MetadataSchemaRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, schema_id: uuid.UUID
    ) -> MetadataSchema | None: ...

    @abstractmethod
    async def get_by_slug(self, organization_id: uuid.UUID, slug: str) -> MetadataSchema | None: ...

    @abstractmethod
    async def add(self, schema: MetadataSchema) -> MetadataSchema: ...

    @abstractmethod
    async def update(self, schema: MetadataSchema) -> MetadataSchema: ...

    @abstractmethod
    async def list_for_organization(
        self,
        organization_id: uuid.UUID,
        *,
        resource_type: str | None = None,
        active_only: bool = True,
    ) -> Sequence[MetadataSchema]: ...


class MetadataValueRepository(ABC):
    @abstractmethod
    async def get_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        *,
        schema_id: uuid.UUID | None = None,
    ) -> MetadataValue | None: ...

    @abstractmethod
    async def upsert(self, value: MetadataValue) -> MetadataValue: ...

    @abstractmethod
    async def delete_for_resource(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
    ) -> None: ...

    @abstractmethod
    async def search(self, query: MetadataQueryFilter) -> Sequence[MetadataValue]: ...

    @abstractmethod
    async def bulk_delete_for_resources(
        self,
        organization_id: uuid.UUID,
        resource_type: str,
        resource_ids: list[uuid.UUID],
    ) -> int: ...
