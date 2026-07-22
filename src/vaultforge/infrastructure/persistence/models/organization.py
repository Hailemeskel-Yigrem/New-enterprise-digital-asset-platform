"""SQLAlchemy model for organizations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vaultforge.infrastructure.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from vaultforge.infrastructure.persistence.models.membership import MembershipModel
    from vaultforge.infrastructure.persistence.models.team import TeamModel


class OrganizationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    plan_code: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")
    max_storage_gb: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    memberships: Mapped[list[MembershipModel]] = relationship(
        "MembershipModel",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    teams: Mapped[list[TeamModel]] = relationship(
        "TeamModel",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
