"""Organization settings persistence model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vaultforge.domain.assets.enums import SensitivityLabel
from vaultforge.infrastructure.persistence.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationSettingsModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organization_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    default_sensitivity: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SensitivityLabel.INTERNAL.value,
    )
    require_version_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_upload_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    extra: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
