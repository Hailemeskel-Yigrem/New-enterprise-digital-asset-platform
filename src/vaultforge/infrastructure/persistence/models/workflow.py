"""SQLAlchemy models for approval workflows."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vaultforge.infrastructure.persistence.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ApprovalWorkflowModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "approval_workflows"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    steps: Mapped[list[WorkflowStepModel]] = relationship(
        "WorkflowStepModel",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowStepModel.order",
    )


class WorkflowStepModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        UniqueConstraint("workflow_id", "order", name="uq_workflow_steps_workflow_order"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False, default="approval")
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workflow: Mapped[ApprovalWorkflowModel] = relationship(
        "ApprovalWorkflowModel",
        back_populates="steps",
    )


class WorkflowInstanceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "workflow_instances"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_workflows.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="in_progress")
    current_step_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    step_instances: Mapped[list[StepInstanceModel]] = relationship(
        "StepInstanceModel",
        back_populates="instance",
        cascade="all, delete-orphan",
        order_by="StepInstanceModel.order",
    )


class StepInstanceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "step_instances"
    __table_args__ = (
        UniqueConstraint("instance_id", "order", name="uq_step_instances_instance_order"),
    )

    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False, default="approval")
    assignee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="")

    instance: Mapped[WorkflowInstanceModel] = relationship(
        "WorkflowInstanceModel",
        back_populates="step_instances",
    )
