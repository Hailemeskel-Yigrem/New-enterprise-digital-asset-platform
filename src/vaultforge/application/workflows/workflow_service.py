"""Approval workflow application service."""

from __future__ import annotations

import uuid

from vaultforge.application.workflows.schemas import (
    StepInstanceResponse,
    WorkflowDefineRequest,
    WorkflowInstanceResponse,
    WorkflowInstanceStartRequest,
    WorkflowResponse,
    WorkflowStepResponse,
)
from vaultforge.core.exceptions import ConflictError, NotFoundError, ValidationError
from vaultforge.domain.assets.repositories import DocumentRepository
from vaultforge.domain.workflows.entities import (
    ApprovalWorkflow,
    StepInstance,
    WorkflowInstance,
    WorkflowStep,
)
from vaultforge.domain.workflows.enums import StepDecision, WorkflowStatus
from vaultforge.domain.workflows.repositories import (
    StepInstanceRepository,
    WorkflowInstanceRepository,
    WorkflowRepository,
    WorkflowStepRepository,
)


class WorkflowService:
    def __init__(
        self,
        workflow_repo: WorkflowRepository,
        step_repo: WorkflowStepRepository,
        instance_repo: WorkflowInstanceRepository,
        step_instance_repo: StepInstanceRepository,
        document_repo: DocumentRepository,
    ) -> None:
        self._workflows = workflow_repo
        self._steps = step_repo
        self._instances = instance_repo
        self._step_instances = step_instance_repo
        self._documents = document_repo

    async def define_template(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: WorkflowDefineRequest,
    ) -> WorkflowResponse:
        orders = [step.order for step in payload.steps]
        if len(orders) != len(set(orders)):
            raise ValidationError("Step orders must be unique")

        workflow = ApprovalWorkflow(
            organization_id=organization_id,
            name=payload.name.strip(),
            description=payload.description.strip(),
            status=WorkflowStatus.ACTIVE,
            created_by=user_id,
        )
        saved_workflow = await self._workflows.add(workflow)

        steps: list[WorkflowStep] = []
        for definition in sorted(payload.steps, key=lambda item: item.order):
            step = WorkflowStep(
                workflow_id=saved_workflow.id,
                order=definition.order,
                name=definition.name.strip(),
                step_type=definition.step_type,
                assignee_id=definition.assignee_id,
                required=definition.required,
            )
            steps.append(step)

        saved_steps = list(await self._steps.add_many(steps))
        saved_workflow.steps = saved_steps
        return self._to_workflow_response(saved_workflow)

    async def start_instance(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: WorkflowInstanceStartRequest,
    ) -> WorkflowInstanceResponse:
        workflow = await self._require_workflow(organization_id, payload.workflow_id)
        document = await self._documents.get_by_id(organization_id, payload.document_id)
        if document is None:
            raise NotFoundError("Document not found")

        template_steps = list(await self._steps.list_for_workflow(workflow.id))
        if not template_steps:
            raise ValidationError("Workflow template has no steps")

        instance = WorkflowInstance(
            organization_id=organization_id,
            workflow_id=workflow.id,
            document_id=payload.document_id,
            status=WorkflowStatus.IN_PROGRESS,
            current_step_order=min(step.order for step in template_steps),
            started_by=user_id,
        )
        saved_instance = await self._instances.add(instance)

        step_instances = [
            StepInstance(
                instance_id=saved_instance.id,
                step_id=step.id,
                order=step.order,
                name=step.name,
                step_type=step.step_type,
                assignee_id=step.assignee_id or user_id,
            )
            for step in sorted(template_steps, key=lambda item: item.order)
        ]
        saved_step_instances = list(await self._step_instances.add_many(step_instances))
        saved_instance.step_instances = saved_step_instances
        return self._to_instance_response(saved_instance)

    async def approve_step(
        self,
        organization_id: uuid.UUID,
        instance_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        comment: str = "",
    ) -> WorkflowInstanceResponse:
        instance = await self._require_instance(organization_id, instance_id)
        instance.approve_step(user_id, comment=comment)
        await self._persist_instance(instance)
        return self._to_instance_response(instance)

    async def reject_step(
        self,
        organization_id: uuid.UUID,
        instance_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        comment: str,
    ) -> WorkflowInstanceResponse:
        instance = await self._require_instance(organization_id, instance_id)
        instance.reject_step(user_id, comment=comment)
        await self._persist_instance(instance)
        return self._to_instance_response(instance)

    async def advance(
        self,
        organization_id: uuid.UUID,
        instance_id: uuid.UUID,
    ) -> WorkflowInstanceResponse:
        instance = await self._require_instance(organization_id, instance_id)
        current = instance.current_step()
        if current is not None and current.status == StepDecision.PENDING:
            raise ConflictError("Current step must be decided before advancing")
        instance.advance()
        await self._persist_instance(instance)
        return self._to_instance_response(instance)

    async def get_instance(
        self,
        organization_id: uuid.UUID,
        instance_id: uuid.UUID,
    ) -> WorkflowInstanceResponse:
        instance = await self._require_instance(organization_id, instance_id)
        return self._to_instance_response(instance)

    async def list_workflows(self, organization_id: uuid.UUID) -> list[WorkflowResponse]:
        workflows = await self._workflows.list_for_organization(organization_id)
        responses: list[WorkflowResponse] = []
        for workflow in workflows:
            workflow.steps = list(await self._steps.list_for_workflow(workflow.id))
            responses.append(self._to_workflow_response(workflow))
        return responses

    async def _require_workflow(
        self, organization_id: uuid.UUID, workflow_id: uuid.UUID
    ) -> ApprovalWorkflow:
        workflow = await self._workflows.get_by_id(organization_id, workflow_id)
        if workflow is None:
            raise NotFoundError("Workflow template not found")
        if workflow.status != WorkflowStatus.ACTIVE:
            raise ConflictError("Workflow template is not active")
        return workflow

    async def _require_instance(
        self, organization_id: uuid.UUID, instance_id: uuid.UUID
    ) -> WorkflowInstance:
        instance = await self._instances.get_by_id(organization_id, instance_id)
        if instance is None:
            raise NotFoundError("Workflow instance not found")
        instance.step_instances = list(await self._step_instances.list_for_instance(instance.id))
        return instance

    async def _persist_instance(self, instance: WorkflowInstance) -> None:
        await self._instances.update(instance)
        for step in instance.step_instances:
            await self._step_instances.update(step)

    def _to_workflow_response(self, workflow: ApprovalWorkflow) -> WorkflowResponse:
        return WorkflowResponse(
            id=workflow.id,
            organization_id=workflow.organization_id,
            name=workflow.name,
            description=workflow.description,
            status=workflow.status,
            created_by=workflow.created_by,
            steps=[WorkflowStepResponse.model_validate(step) for step in workflow.ordered_steps()],
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )

    def _to_instance_response(self, instance: WorkflowInstance) -> WorkflowInstanceResponse:
        return WorkflowInstanceResponse(
            id=instance.id,
            organization_id=instance.organization_id,
            workflow_id=instance.workflow_id,
            document_id=instance.document_id,
            status=instance.status,
            current_step_order=instance.current_step_order,
            started_by=instance.started_by,
            completed_at=instance.completed_at,
            step_instances=[
                StepInstanceResponse.model_validate(step)
                for step in instance.ordered_step_instances()
            ],
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )
