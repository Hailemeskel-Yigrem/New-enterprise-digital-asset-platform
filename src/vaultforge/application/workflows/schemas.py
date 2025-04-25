"""Pydantic DTOs for workflow operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from vaultforge.domain.workflows.enums import StepDecision, StepType, WorkflowStatus


class WorkflowStepDefinition(BaseModel):
    order: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=255)
    step_type: StepType = StepType.APPROVAL
    assignee_id: uuid.UUID
    required: bool = True


class WorkflowDefineRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    steps: list[WorkflowStepDefinition] = Field(min_length=1)


class WorkflowStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    order: int
    name: str
    step_type: StepType
    assignee_id: uuid.UUID | None
    required: bool
    created_at: datetime
    updated_at: datetime


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: str
    status: WorkflowStatus
    created_by: uuid.UUID
    steps: list[WorkflowStepResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WorkflowInstanceStartRequest(BaseModel):
    workflow_id: uuid.UUID
    document_id: uuid.UUID


class StepInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instance_id: uuid.UUID
    step_id: uuid.UUID
    order: int
    name: str
    step_type: StepType
    assignee_id: uuid.UUID
    status: StepDecision
    decided_by: uuid.UUID | None
    decided_at: datetime | None
    comment: str
    created_at: datetime
    updated_at: datetime


class WorkflowInstanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    workflow_id: uuid.UUID
    document_id: uuid.UUID
    status: WorkflowStatus
    current_step_order: int
    started_by: uuid.UUID
    completed_at: datetime | None
    step_instances: list[StepInstanceResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class StepDecisionRequest(BaseModel):
    comment: str = ""


class StepRejectRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)
