"""Organization settings table.

Revision ID: 20250601_0005
Revises: 20250520_0004
Create Date: 2025-06-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20250601_0005"
down_revision = "20250520_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organization_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_sensitivity", sa.String(length=32), nullable=False, server_default="internal"),
        sa.Column("require_version_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("max_upload_mb", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("extra", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_organization_settings_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organization_settings")),
        sa.UniqueConstraint(
            "organization_id", name=op.f("uq_organization_settings_organization_id")
        ),
    )
    op.create_index(
        op.f("ix_organization_settings_organization_id"),
        "organization_settings",
        ["organization_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_organization_settings_organization_id"), table_name="organization_settings"
    )
    op.drop_table("organization_settings")
