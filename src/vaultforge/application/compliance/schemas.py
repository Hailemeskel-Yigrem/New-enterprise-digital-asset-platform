"""Compliance API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from vaultforge.domain.compliance.enums import (
    ClassificationLevel,
    ComplianceHoldStatus,
    ExportFormat,
    ExportStatus,
)


class ClassificationLabelCreateRequest(BaseModel):
    name: str
    level: ClassificationLevel
    color: str = "#64748b"
    description: str = ""
    is_default: bool = False


class ClassificationLabelResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    level: ClassificationLevel
    color: str
    description: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignClassificationRequest(BaseModel):
    resource_id: uuid.UUID
    label_id: uuid.UUID
    justification: str = ""


class ComplianceHoldCreateRequest(BaseModel):
    name: str
    matter_id: str = ""
    description: str = ""
    resource_ids: list[uuid.UUID] = Field(default_factory=list)
    folder_ids: list[uuid.UUID] = Field(default_factory=list)


class ComplianceHoldResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    matter_id: str
    description: str
    status: ComplianceHoldStatus
    resource_ids: list[uuid.UUID]
    folder_ids: list[uuid.UUID]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExportPackageRequest(BaseModel):
    format: ExportFormat = ExportFormat.ZIP
    include_metadata: bool = True
    include_audit_trail: bool = False


class ExportPackageResponse(BaseModel):
    id: uuid.UUID
    hold_id: uuid.UUID
    manifest_id: uuid.UUID
    format: ExportFormat
    status: ExportStatus
    storage_key: str
    error_message: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
