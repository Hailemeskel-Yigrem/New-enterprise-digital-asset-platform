"""SQLAlchemy models for teams and team membership."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vaultforge.infrastructure.persistence.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from vaultforge.infrastructure.persistence.models.organization import OrganizationModel
    from vaultforge.infrastructure.persistence.models.user import UserModel


class TeamModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "teams"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    organization: Mapped[OrganizationModel] = relationship(
        "OrganizationModel",
        back_populates="teams",
    )
    members: Mapped[list[TeamMemberModel]] = relationship(
        "TeamMemberModel",
        back_populates="team",
        cascade="all, delete-orphan",
    )


class TeamMemberModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),)

    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    team: Mapped[TeamModel] = relationship("TeamModel", back_populates="members")
    user: Mapped[UserModel] = relationship("UserModel", back_populates="team_memberships")
