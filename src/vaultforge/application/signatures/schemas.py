"""Pydantic DTOs for signature operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vaultforge.domain.signatures.enums import SignatureRequestStatus, SignerStatus


class SignerDefinition(BaseModel):
    user_id: uuid.UUID
    order: int = Field(ge=1)


class SignatureRequestCreateRequest(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    message: str = ""
    signers: list[SignerDefinition] = Field(min_length=1)


class SignerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_id: uuid.UUID
    user_id: uuid.UUID
    order: int
    status: SignerStatus
    signature_hash: str | None
    signed_at: datetime | None
    declined_at: datetime | None
    decline_reason: str
    created_at: datetime
    updated_at: datetime


class SignatureRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    document_checksum: str
    title: str
    message: str
    status: SignatureRequestStatus
    created_by: uuid.UUID
    completed_at: datetime | None
    signers: list[SignerResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SignDocumentResponse(BaseModel):
    request_id: uuid.UUID
    signature_hash: str
    status: SignatureRequestStatus


class DeclineSignatureRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)
