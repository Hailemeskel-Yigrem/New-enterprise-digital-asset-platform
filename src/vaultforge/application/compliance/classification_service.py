"""Classification label and policy application service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.application.compliance.schemas import (
    AssignClassificationRequest,
    ClassificationLabelCreateRequest,
    ClassificationLabelResponse,
)
from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.domain.compliance.entities import ClassificationLabel, ClassificationPolicy
from vaultforge.domain.compliance.repositories import (
    ClassificationLabelRepository,
    ClassificationPolicyRepository,
)


@dataclass(slots=True)
class ResourceClassificationStore:
    """In-memory classification assignments for documents."""

    _assignments: dict[tuple[uuid.UUID, uuid.UUID], uuid.UUID]

    def __init__(self) -> None:
        self._assignments = {}

    async def get_label_id(
        self, organization_id: uuid.UUID, resource_id: uuid.UUID
    ) -> uuid.UUID | None:
        return self._assignments.get((organization_id, resource_id))

    async def set_label_id(
        self, organization_id: uuid.UUID, resource_id: uuid.UUID, label_id: uuid.UUID
    ) -> None:
        self._assignments[(organization_id, resource_id)] = label_id


@dataclass(slots=True)
class ClassificationService:
    labels: ClassificationLabelRepository
    policies: ClassificationPolicyRepository
    assignments: ResourceClassificationStore

    async def create_label(
        self,
        organization_id: uuid.UUID,
        payload: ClassificationLabelCreateRequest,
    ) -> ClassificationLabelResponse:
        label = ClassificationLabel(
            organization_id=organization_id,
            name=payload.name,
            level=payload.level,
            color=payload.color,
            description=payload.description,
            is_default=payload.is_default,
        )
        saved = await self.labels.add(label)
        return ClassificationLabelResponse.model_validate(saved)

    async def list_labels(self, organization_id: uuid.UUID) -> list[ClassificationLabelResponse]:
        labels = await self.labels.list_for_organization(organization_id)
        return [ClassificationLabelResponse.model_validate(label) for label in labels]

    async def assign_classification(
        self,
        organization_id: uuid.UUID,
        payload: AssignClassificationRequest,
    ) -> ClassificationLabelResponse:
        label = await self.labels.get_by_id(organization_id, payload.label_id)
        if label is None:
            raise NotFoundError("Classification label not found")
        if label.requires_justification and not payload.justification.strip():
            raise ValidationError("Justification required for this classification level")
        policy = await self.policies.get_active(organization_id)
        current_label_id = await self.assignments.get_label_id(organization_id, payload.resource_id)
        if policy is not None and current_label_id is not None:
            current = await self.labels.get_by_id(organization_id, current_label_id)
            if current is not None and not policy.is_transition_allowed(current.level, label.level):
                raise ValidationError("Classification downgrade not permitted")
        await self.assignments.set_label_id(organization_id, payload.resource_id, label.id)
        return ClassificationLabelResponse.model_validate(label)

    async def ensure_default_policy(self, organization_id: uuid.UUID) -> ClassificationPolicy:
        policy = await self.policies.get_active(organization_id)
        if policy is not None:
            return policy
        created = ClassificationPolicy(
            organization_id=organization_id,
            name="Default Classification Policy",
            enforce_on_upload=True,
            block_downgrade=True,
        )
        return await self.policies.upsert(created)
