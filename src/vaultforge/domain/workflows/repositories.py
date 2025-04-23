"""Repository interfaces for workflow aggregates."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Sequence

from vaultforge.domain.workflows.entities import (
    ApprovalWorkflow,
    StepInstance,
    WorkflowInstance,
    WorkflowStep,
)


class WorkflowRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, workflow_id: uuid.UUID
    ) -> ApprovalWorkflow | None: ...

    @abstractmethod
    async def add(self, workflow: ApprovalWorkflow) -> ApprovalWorkflow: ...

    @abstractmethod
    async def update(self, workflow: ApprovalWorkflow) -> ApprovalWorkflow: ...

    @abstractmethod
    async def list_for_organization(
        self, organization_id: uuid.UUID
    ) -> Sequence[ApprovalWorkflow]: ...


class WorkflowStepRepository(ABC):
    @abstractmethod
    async def list_for_workflow(self, workflow_id: uuid.UUID) -> Sequence[WorkflowStep]: ...

    @abstractmethod
    async def add(self, step: WorkflowStep) -> WorkflowStep: ...

    @abstractmethod
    async def add_many(self, steps: Sequence[WorkflowStep]) -> Sequence[WorkflowStep]: ...


class WorkflowInstanceRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, instance_id: uuid.UUID
    ) -> WorkflowInstance | None: ...

    @abstractmethod
    async def add(self, instance: WorkflowInstance) -> WorkflowInstance: ...

    @abstractmethod
    async def update(self, instance: WorkflowInstance) -> WorkflowInstance: ...

    @abstractmethod
    async def list_for_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> Sequence[WorkflowInstance]: ...


class StepInstanceRepository(ABC):
    @abstractmethod
    async def list_for_instance(self, instance_id: uuid.UUID) -> Sequence[StepInstance]: ...

    @abstractmethod
    async def add_many(self, steps: Sequence[StepInstance]) -> Sequence[StepInstance]: ...

    @abstractmethod
    async def update(self, step: StepInstance) -> StepInstance: ...
