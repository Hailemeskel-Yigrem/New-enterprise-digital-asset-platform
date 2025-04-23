"""Approval workflow aggregates."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from vaultforge.core.exceptions import AuthorizationError, ConflictError, ValidationError
from vaultforge.domain.common import Entity, utc_now
from vaultforge.domain.workflows.enums import StepDecision, StepType, WorkflowStatus


def _require_non_empty(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty")
    return cleaned


@dataclass(slots=True)
class WorkflowStep(Entity):
    workflow_id: uuid.UUID = field(default_factory=uuid.uuid4)
    order: int = 1
    name: str = ""
    step_type: StepType = StepType.APPROVAL
    assignee_id: uuid.UUID | None = None
    required: bool = True

    def rename(self, new_name: str) -> None:
        self.name = _require_non_empty(new_name, "Step name")
        self.touch()


@dataclass(slots=True)
class ApprovalWorkflow(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    description: str = ""
    status: WorkflowStatus = WorkflowStatus.ACTIVE
    created_by: uuid.UUID = field(default_factory=uuid.uuid4)
    steps: list[WorkflowStep] = field(default_factory=list)

    def rename(self, new_name: str) -> None:
        self.name = _require_non_empty(new_name, "Workflow name")
        self.touch()

    def add_step(self, step: WorkflowStep) -> None:
        if step.workflow_id != self.id:
            raise ValidationError("Step does not belong to this workflow")
        if any(existing.order == step.order for existing in self.steps):
            raise ConflictError(f"Step order {step.order} already exists")
        self.steps.append(step)
        self.steps.sort(key=lambda item: item.order)
        self.touch()

    def ordered_steps(self) -> list[WorkflowStep]:
        return sorted(self.steps, key=lambda item: item.order)


@dataclass(slots=True)
class StepInstance(Entity):
    instance_id: uuid.UUID = field(default_factory=uuid.uuid4)
    step_id: uuid.UUID = field(default_factory=uuid.uuid4)
    order: int = 1
    name: str = ""
    step_type: StepType = StepType.APPROVAL
    assignee_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: StepDecision = StepDecision.PENDING
    decided_by: uuid.UUID | None = None
    decided_at: datetime | None = None
    comment: str = ""

    def approve(self, user_id: uuid.UUID, *, comment: str = "") -> None:
        self._ensure_pending()
        if self.assignee_id != user_id:
            raise AuthorizationError("Only the assigned approver may approve this step")
        self.status = StepDecision.APPROVED
        self.decided_by = user_id
        self.decided_at = utc_now()
        self.comment = comment.strip()
        self.touch()

    def reject(self, user_id: uuid.UUID, *, comment: str = "") -> None:
        self._ensure_pending()
        if self.assignee_id != user_id:
            raise AuthorizationError("Only the assigned approver may reject this step")
        if not comment.strip():
            raise ValidationError("Rejection requires a comment")
        self.status = StepDecision.REJECTED
        self.decided_by = user_id
        self.decided_at = utc_now()
        self.comment = comment.strip()
        self.touch()

    def skip(self) -> None:
        self._ensure_pending()
        self.status = StepDecision.SKIPPED
        self.decided_at = utc_now()
        self.touch()

    def _ensure_pending(self) -> None:
        if self.status != StepDecision.PENDING:
            raise ConflictError("Step is no longer pending")


@dataclass(slots=True)
class WorkflowInstance(Entity):
    organization_id: uuid.UUID = field(default_factory=uuid.uuid4)
    workflow_id: uuid.UUID = field(default_factory=uuid.uuid4)
    document_id: uuid.UUID = field(default_factory=uuid.uuid4)
    status: WorkflowStatus = WorkflowStatus.IN_PROGRESS
    current_step_order: int = 1
    started_by: uuid.UUID = field(default_factory=uuid.uuid4)
    completed_at: datetime | None = None
    step_instances: list[StepInstance] = field(default_factory=list)

    def ordered_step_instances(self) -> list[StepInstance]:
        return sorted(self.step_instances, key=lambda item: item.order)

    def current_step(self) -> StepInstance | None:
        for step in self.ordered_step_instances():
            if step.status == StepDecision.PENDING:
                return step
        return None

    def approve_step(self, user_id: uuid.UUID, *, comment: str = "") -> None:
        self._ensure_in_progress()
        step = self.current_step()
        if step is None:
            raise ConflictError("Workflow has no pending steps")
        step.approve(user_id, comment=comment)
        self.advance()

    def reject_step(self, user_id: uuid.UUID, *, comment: str = "") -> None:
        self._ensure_in_progress()
        step = self.current_step()
        if step is None:
            raise ConflictError("Workflow has no pending steps")
        step.reject(user_id, comment=comment)
        self.status = WorkflowStatus.REJECTED
        self.completed_at = utc_now()
        self.touch()

    def advance(self) -> None:
        """Move to the next pending step or mark the workflow completed."""
        self._ensure_in_progress()
        pending = self.current_step()
        if pending is not None:
            self.current_step_order = pending.order
            self.touch()
            return
        self.status = WorkflowStatus.COMPLETED
        self.completed_at = utc_now()
        self.touch()

    def cancel(self) -> None:
        if self.status in {
            WorkflowStatus.COMPLETED,
            WorkflowStatus.REJECTED,
            WorkflowStatus.CANCELLED,
        }:
            raise ConflictError("Workflow instance is already terminal")
        self.status = WorkflowStatus.CANCELLED
        self.completed_at = utc_now()
        self.touch()

    def _ensure_in_progress(self) -> None:
        if self.status != WorkflowStatus.IN_PROGRESS:
            raise ConflictError("Workflow instance is not in progress")
