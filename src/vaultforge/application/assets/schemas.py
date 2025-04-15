"""Pydantic DTOs for asset operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vaultforge.domain.assets.enums import DocumentStatus, FolderKind, SensitivityLabel, VersionStatus


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    kind: FolderKind = FolderKind.STANDARD
    description: str = ""


class FolderRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FolderMoveRequest(BaseModel):
    parent_id: uuid.UUID | None = None


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    kind: FolderKind
    description: str
    created_at: datetime
    updated_at: datetime


class DocumentUploadRequest(BaseModel):
    folder_id: uuid.UUID
    name: str = Field(min_length=1, max_length=512)
    sensitivity: SensitivityLabel = SensitivityLabel.INTERNAL
    tags: list[str] = Field(default_factory=list)
    comment: str = ""


class DocumentVersionCreateRequest(BaseModel):
    comment: str = ""


class DocumentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    sensitivity: SensitivityLabel | None = None
    tags: list[str] | None = None


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    checksum_sha256: str
    content_type: str
    size_bytes: int
    status: VersionStatus
    created_by: uuid.UUID
    comment: str
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    folder_id: uuid.UUID
    name: str
    status: DocumentStatus
    sensitivity: SensitivityLabel
    tags: list[str]
    current_version_id: uuid.UUID | None
    created_by: uuid.UUID
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
    current_version: DocumentVersionResponse | None = None


class DocumentSearchRequest(BaseModel):
    name: str | None = None
    status: DocumentStatus | None = None
    folder_id: uuid.UUID | None = None
    tags: list[str] = Field(default_factory=list)
    include_deleted: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class DocumentSearchResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class CheckoutResponse(BaseModel):
    lock_id: uuid.UUID
    document_id: uuid.UUID
    locked_by: uuid.UUID
    locked_at: datetime
    expires_at: datetime | None
