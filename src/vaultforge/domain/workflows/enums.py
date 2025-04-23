"""Workflow domain enumerations."""

from __future__ import annotations

from enum import Enum


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class StepType(str, Enum):
    APPROVAL = "approval"
    REVIEW = "review"
    NOTIFICATION = "notification"


class StepDecision(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"
