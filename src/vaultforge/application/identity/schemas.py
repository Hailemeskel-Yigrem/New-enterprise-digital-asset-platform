"""Pydantic DTOs for identity and access APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from vaultforge.domain.identity.enums import MembershipStatus, OrgRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_email_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    plan_code: str = Field(default="standard", max_length=50)
    max_storage_gb: int = Field(default=100, ge=1)


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    plan_code: str | None = Field(default=None, max_length=50)
    max_storage_gb: int | None = Field(default=None, ge=1)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_active: bool
    plan_code: str
    max_storage_gb: int
    created_at: datetime
    updated_at: datetime


class InviteMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(default="", max_length=255)
    role: OrgRole = OrgRole.VIEWER


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: OrgRole
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    member_ids: list[uuid.UUID] = Field(default_factory=list)


class TeamMemberAddRequest(BaseModel):
    user_id: uuid.UUID


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str
    member_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime
