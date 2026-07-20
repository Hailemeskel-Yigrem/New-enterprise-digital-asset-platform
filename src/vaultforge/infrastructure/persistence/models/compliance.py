"""SQLAlchemy models for compliance."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vaultforge.infrastructure.persistence.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ClassificationLabelModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "classification_labels"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#64748b")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_default: Mapped[bool] = mapped_column(nullable=False, default=False)


class ClassificationPolicyModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "classification_policies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    default_label_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    enforce_on_upload: Mapped[bool] = mapped_column(nullable=False, default=True)
    block_downgrade: Mapped[bool] = mapped_column(nullable=False, default=True)
    allowed_transitions_json: Mapped[dict[str, list[str]]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)


class ComplianceHoldModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "compliance_holds"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    matter_id: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    released_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resource_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    folder_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )
    custodian_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, default=list
    )


class ExportManifestModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "export_manifests"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    hold_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    entries_json: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False, default=list)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")


class ExportPackageModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "export_packages"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    hold_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    manifest_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="zip")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    requested_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False, default="")
