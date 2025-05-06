"""Pydantic DTOs for audit and activity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditEventCreateRequest(BaseModel):
    action: str = Field(min_length=1, max_length=128)
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: uuid.UUID
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    resource_type: str
    resource_id: uuid.UUID
    metadata: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    updated_at: datetime


class AuditTimelineQuery(BaseModel):
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    actor_id: uuid.UUID | None = None
    action: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class AuditTimelineResponse(BaseModel):
    events: list[AuditEventResponse]
    total: int


class ActivityItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    activity_type: str
    summary: str
    resource_type: str
    resource_id: uuid.UUID
    audit_event_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class ActivityFeedQuery(BaseModel):
    user_id: uuid.UUID | None = None
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ActivityFeedResponse(BaseModel):
    items: list[ActivityItemResponse]
    total: int
