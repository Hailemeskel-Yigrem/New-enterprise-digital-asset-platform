"""Unit tests for workflow instance advance logic."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import AuthorizationError, ConflictError
from vaultforge.domain.workflows.entities import StepInstance, WorkflowInstance
from vaultforge.domain.workflows.enums import StepType, WorkflowStatus


def _build_instance(*assignees: uuid.UUID) -> WorkflowInstance:
    instance_id = uuid.uuid4()
    steps = [
        StepInstance(
            instance_id=instance_id,
            step_id=uuid.uuid4(),
            order=index + 1,
            name=f"Step {index + 1}",
            step_type=StepType.APPROVAL,
            assignee_id=assignee,
        )
        for index, assignee in enumerate(assignees)
    ]
    return WorkflowInstance(
        id=instance_id,
        step_instances=steps,
        current_step_order=1,
        status=WorkflowStatus.IN_PROGRESS,
    )


def test_advance_moves_to_next_step_after_approval() -> None:
    first = uuid.uuid4()
    second = uuid.uuid4()
    instance = _build_instance(first, second)

    instance.approve_step(first)
    assert instance.status == WorkflowStatus.IN_PROGRESS
    assert instance.current_step_order == 2
    assert instance.current_step() is not None
    assert instance.current_step().assignee_id == second


def test_advance_completes_when_all_steps_approved() -> None:
    approver = uuid.uuid4()
    instance = _build_instance(approver)

    instance.approve_step(approver)
    assert instance.status == WorkflowStatus.COMPLETED
    assert instance.completed_at is not None
    assert instance.current_step() is None


def test_reject_step_marks_instance_rejected() -> None:
    approver = uuid.uuid4()
    instance = _build_instance(approver, uuid.uuid4())

    instance.reject_step(approver, comment="Needs revision")
    assert instance.status == WorkflowStatus.REJECTED
    assert instance.completed_at is not None


def test_approve_step_requires_assignee() -> None:
    approver = uuid.uuid4()
    other = uuid.uuid4()
    instance = _build_instance(approver)

    with pytest.raises(AuthorizationError, match="assigned approver"):
        instance.approve_step(other)


def test_advance_on_completed_instance_raises() -> None:
    approver = uuid.uuid4()
    instance = _build_instance(approver)
    instance.approve_step(approver)

    with pytest.raises(ConflictError, match="not in progress"):
        instance.advance()
