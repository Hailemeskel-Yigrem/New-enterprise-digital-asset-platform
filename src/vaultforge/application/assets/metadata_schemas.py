"""Pydantic schemas for metadata API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MetadataFieldDefinitionRequest(BaseModel):
    key: str
    label: str
    field_type: str
    required: bool = False
    description: str = ""
    default_value: Any = None
    enum_options: list[str] = Field(default_factory=list)
    searchable: bool = True
    sort_order: int = 0


class MetadataSchemaCreateRequest(BaseModel):
    name: str
    slug: str
    description: str = ""
    resource_type: str = "document"
    fields: list[MetadataFieldDefinitionRequest]


class MetadataSchemaUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    fields: list[MetadataFieldDefinitionRequest] | None = None


class MetadataSchemaResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    description: str
    resource_type: str
    version: int
    is_active: bool
    fields: list[MetadataFieldDefinitionRequest]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetadataValueUpsertRequest(BaseModel):
    values: dict[str, Any]


class MetadataValueResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    schema_id: uuid.UUID
    schema_version: int
    resource_type: str
    resource_id: uuid.UUID
    values: dict[str, Any]
    updated_by: uuid.UUID
    updated_at: datetime

    model_config = {"from_attributes": True}
