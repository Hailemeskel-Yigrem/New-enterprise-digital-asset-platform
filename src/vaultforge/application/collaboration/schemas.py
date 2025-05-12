"""Pydantic DTOs for collaboration."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CommentCreateRequest(BaseModel):
    resource_type: str = Field(min_length=1, max_length=64)
    resource_id: uuid.UUID
    body: str = Field(min_length=1, max_length=10000)
    parent_id: uuid.UUID | None = None


class CommentUpdateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class MentionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    comment_id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    parent_id: uuid.UUID | None
    edited_at: datetime | None
    deleted_at: datetime | None
    mentions: list[MentionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    body: str
    notification_type: str
    resource_type: str | None
    resource_id: uuid.UUID | None
    read_at: datetime | None
    is_read: bool
    created_at: datetime
    updated_at: datetime


class NotificationListQuery(BaseModel):
    unread_only: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
