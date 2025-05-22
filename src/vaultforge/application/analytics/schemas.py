"""Pydantic schemas for analytics, reports, and global search."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel


class ActivityKind(StrEnum):
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated"
    VERSION_UPLOADED = "version_uploaded"
    FOLDER_CREATED = "folder_created"


class DashboardStatsResponse(BaseModel):
    document_count: int
    folder_count: int
    pending_approvals: int
    storage_used_bytes: int
    storage_limit_bytes: int


class RecentActivityItem(BaseModel):
    kind: ActivityKind
    resource_id: uuid.UUID
    resource_name: str
    actor_id: uuid.UUID | None = None
    occurred_at: datetime


class DashboardResponse(BaseModel):
    stats: DashboardStatsResponse
    recent_activity: list[RecentActivityItem]


class ReportDimension(StrEnum):
    USER = "user"
    FOLDER = "folder"
    SENSITIVITY = "sensitivity"


class ReportRow(BaseModel):
    key: str
    label: str
    document_count: int
    storage_bytes: int


class UsageReportRequest(BaseModel):
    dimension: ReportDimension
    limit: int = Field(default=50, ge=1, le=500)


class UsageReportResponse(BaseModel):
    organization_id: uuid.UUID
    dimension: ReportDimension
    rows: list[ReportRow]
    generated_at: datetime


class GlobalSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=255)
    limit: int = Field(default=25, ge=1, le=100)


class SearchDocumentHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    folder_id: uuid.UUID
    status: DocumentStatus
    sensitivity: SensitivityLabel
    updated_at: datetime


class SearchFolderHit(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    updated_at: datetime


class GlobalSearchResponse(BaseModel):
    query: str
    documents: list[SearchDocumentHit]
    folders: list[SearchFolderHit]
    total_hits: int
