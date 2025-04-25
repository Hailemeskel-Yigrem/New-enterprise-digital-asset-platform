"""SQLAlchemy workflow repositories."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from vaultforge.domain.workflows.entities import (
    ApprovalWorkflow,
    StepInstance,
    WorkflowInstance,
    WorkflowStep,
)
from vaultforge.domain.workflows.enums import StepDecision, StepType, WorkflowStatus
from vaultforge.domain.workflows.repositories import (
    StepInstanceRepository,
    WorkflowInstanceRepository,
    WorkflowRepository,
    WorkflowStepRepository,
)
from vaultforge.infrastructure.persistence.models.workflow import (
    ApprovalWorkflowModel,
    StepInstanceModel,
    WorkflowInstanceModel,
    WorkflowStepModel,
)


def _workflow_to_entity(model: ApprovalWorkflowModel) -> ApprovalWorkflow:
    return ApprovalWorkflow(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        description=model.description,
        status=WorkflowStatus(model.status),
        created_by=model.created_by,
        steps=[_step_to_entity(step) for step in model.steps],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_workflow(model: ApprovalWorkflowModel, workflow: ApprovalWorkflow) -> None:
    model.organization_id = workflow.organization_id
    model.name = workflow.name
    model.description = workflow.description
    model.status = workflow.status.value
    model.created_by = workflow.created_by
    model.updated_at = workflow.updated_at


def _step_to_entity(model: WorkflowStepModel) -> WorkflowStep:
    return WorkflowStep(
        id=model.id,
        workflow_id=model.workflow_id,
        order=model.order,
        name=model.name,
        step_type=StepType(model.step_type),
        assignee_id=model.assignee_id,
        required=model.required,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _instance_to_entity(model: WorkflowInstanceModel) -> WorkflowInstance:
    return WorkflowInstance(
        id=model.id,
        organization_id=model.organization_id,
        workflow_id=model.workflow_id,
        document_id=model.document_id,
        status=WorkflowStatus(model.status),
        current_step_order=model.current_step_order,
        started_by=model.started_by,
        completed_at=model.completed_at,
        step_instances=[_step_instance_to_entity(step) for step in model.step_instances],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_instance(model: WorkflowInstanceModel, instance: WorkflowInstance) -> None:
    model.organization_id = instance.organization_id
    model.workflow_id = instance.workflow_id
    model.document_id = instance.document_id
    model.status = instance.status.value
    model.current_step_order = instance.current_step_order
    model.started_by = instance.started_by
    model.completed_at = instance.completed_at
    model.updated_at = instance.updated_at


def _step_instance_to_entity(model: StepInstanceModel) -> StepInstance:
    return StepInstance(
        id=model.id,
        instance_id=model.instance_id,
        step_id=model.step_id,
        order=model.order,
        name=model.name,
        step_type=StepType(model.step_type),
        assignee_id=model.assignee_id,
        status=StepDecision(model.status),
        decided_by=model.decided_by,
        decided_at=model.decided_at,
        comment=model.comment,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _apply_step_instance(model: StepInstanceModel, step: StepInstance) -> None:
    model.instance_id = step.instance_id
    model.step_id = step.step_id
    model.order = step.order
    model.name = step.name
    model.step_type = step.step_type.value
    model.assignee_id = step.assignee_id
    model.status = step.status.value
    model.decided_by = step.decided_by
    model.decided_at = step.decided_at
    model.comment = step.comment
    model.updated_at = step.updated_at


class SqlAlchemyWorkflowRepository(WorkflowRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, organization_id: uuid.UUID, workflow_id: uuid.UUID
    ) -> ApprovalWorkflow | None:
        stmt = (
            select(ApprovalWorkflowModel)
            .where(
                ApprovalWorkflowModel.id == workflow_id,
                ApprovalWorkflowModel.organization_id == organization_id,
            )
            .options(selectinload(ApprovalWorkflowModel.steps))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _workflow_to_entity(model) if model else None

    async def add(self, workflow: ApprovalWorkflow) -> ApprovalWorkflow:
        model = ApprovalWorkflowModel(
            id=workflow.id,
            organization_id=workflow.organization_id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status.value,
            created_by=workflow.created_by,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _workflow_to_entity(model)

    async def update(self, workflow: ApprovalWorkflow) -> ApprovalWorkflow:
        model = await self._session.get(ApprovalWorkflowModel, workflow.id)
        if model is None:
            raise ValueError("Workflow not found")
        _apply_workflow(model, workflow)
        await self._session.flush()
        return _workflow_to_entity(model)

    async def list_for_organization(self, organization_id: uuid.UUID) -> list[ApprovalWorkflow]:
        stmt = (
            select(ApprovalWorkflowModel)
            .where(ApprovalWorkflowModel.organization_id == organization_id)
            .options(selectinload(ApprovalWorkflowModel.steps))
            .order_by(ApprovalWorkflowModel.name)
        )
        result = await self._session.execute(stmt)
        return [_workflow_to_entity(model) for model in result.scalars().all()]


class SqlAlchemyWorkflowStepRepository(WorkflowStepRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_workflow(self, workflow_id: uuid.UUID) -> list[WorkflowStep]:
        stmt = (
            select(WorkflowStepModel)
            .where(WorkflowStepModel.workflow_id == workflow_id)
            .order_by(WorkflowStepModel.order)
        )
        result = await self._session.execute(stmt)
        return [_step_to_entity(model) for model in result.scalars().all()]

    async def add(self, step: WorkflowStep) -> WorkflowStep:
        saved = list(await self.add_many([step]))
        return saved[0]

    async def add_many(self, steps: list[WorkflowStep]) -> list[WorkflowStep]:
        models = [
            WorkflowStepModel(
                id=step.id,
                workflow_id=step.workflow_id,
                order=step.order,
                name=step.name,
                step_type=step.step_type.value,
                assignee_id=step.assignee_id,
                required=step.required,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
            for step in steps
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_step_to_entity(model) for model in models]


class SqlAlchemyWorkflowInstanceRepository(WorkflowInstanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, organization_id: uuid.UUID, instance_id: uuid.UUID
    ) -> WorkflowInstance | None:
        stmt = (
            select(WorkflowInstanceModel)
            .where(
                WorkflowInstanceModel.id == instance_id,
                WorkflowInstanceModel.organization_id == organization_id,
            )
            .options(selectinload(WorkflowInstanceModel.step_instances))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return _instance_to_entity(model) if model else None

    async def add(self, instance: WorkflowInstance) -> WorkflowInstance:
        model = WorkflowInstanceModel(
            id=instance.id,
            organization_id=instance.organization_id,
            workflow_id=instance.workflow_id,
            document_id=instance.document_id,
            status=instance.status.value,
            current_step_order=instance.current_step_order,
            started_by=instance.started_by,
            completed_at=instance.completed_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _instance_to_entity(model)

    async def update(self, instance: WorkflowInstance) -> WorkflowInstance:
        model = await self._session.get(WorkflowInstanceModel, instance.id)
        if model is None:
            raise ValueError("Workflow instance not found")
        _apply_instance(model, instance)
        await self._session.flush()
        return _instance_to_entity(model)

    async def list_for_document(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> list[WorkflowInstance]:
        stmt = (
            select(WorkflowInstanceModel)
            .where(
                WorkflowInstanceModel.organization_id == organization_id,
                WorkflowInstanceModel.document_id == document_id,
            )
            .options(selectinload(WorkflowInstanceModel.step_instances))
            .order_by(WorkflowInstanceModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [_instance_to_entity(model) for model in result.scalars().all()]


class SqlAlchemyStepInstanceRepository(StepInstanceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_instance(self, instance_id: uuid.UUID) -> list[StepInstance]:
        stmt = (
            select(StepInstanceModel)
            .where(StepInstanceModel.instance_id == instance_id)
            .order_by(StepInstanceModel.order)
        )
        result = await self._session.execute(stmt)
        return [_step_instance_to_entity(model) for model in result.scalars().all()]

    async def add_many(self, steps: list[StepInstance]) -> list[StepInstance]:
        models = [
            StepInstanceModel(
                id=step.id,
                instance_id=step.instance_id,
                step_id=step.step_id,
                order=step.order,
                name=step.name,
                step_type=step.step_type.value,
                assignee_id=step.assignee_id,
                status=step.status.value,
                decided_by=step.decided_by,
                decided_at=step.decided_at,
                comment=step.comment,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
            for step in steps
        ]
        self._session.add_all(models)
        await self._session.flush()
        return [_step_instance_to_entity(model) for model in models]

    async def update(self, step: StepInstance) -> StepInstance:
        model = await self._session.get(StepInstanceModel, step.id)
        if model is None:
            raise ValueError("Step instance not found")
        _apply_step_instance(model, step)
        await self._session.flush()
        return _step_instance_to_entity(model)
