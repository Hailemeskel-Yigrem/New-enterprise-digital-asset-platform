"""SQLAlchemy model for folders."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vaultforge.domain.assets.enums import FolderKind
from vaultforge.infrastructure.persistence.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FolderModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "folders"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "parent_id",
            "name",
            name="uq_folders_org_parent_name",
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("folders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=FolderKind.STANDARD.value)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
