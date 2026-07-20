"""Unit tests for classification service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from vaultforge.application.compliance.classification_service import (
    ClassificationService,
    ResourceClassificationStore,
)
from vaultforge.application.compliance.schemas import (
    AssignClassificationRequest,
    ClassificationLabelCreateRequest,
)
from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.compliance.entities import ClassificationLabel
from vaultforge.domain.compliance.enums import ClassificationLevel


@pytest.fixture
def label_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.add = AsyncMock(side_effect=lambda label: label)
    repo.list_for_organization = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def policy_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.get_active = AsyncMock(return_value=None)
    repo.upsert = AsyncMock(side_effect=lambda p: p)
    return repo


@pytest.fixture
def service(label_repo: AsyncMock, policy_repo: AsyncMock) -> ClassificationService:
    return ClassificationService(label_repo, policy_repo, ResourceClassificationStore())


@pytest.mark.asyncio
async def test_create_label(service: ClassificationService, label_repo: AsyncMock) -> None:
    payload = ClassificationLabelCreateRequest(
        name="Internal",
        level=ClassificationLevel.INTERNAL,
    )
    result = await service.create_label(uuid.uuid4(), payload)
    assert result.name == "Internal"
    label_repo.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_requires_justification(
    service: ClassificationService, label_repo: AsyncMock
) -> None:
    label = ClassificationLabel(
        name="Restricted", level=ClassificationLevel.RESTRICTED, requires_justification=True
    )
    label_repo.get_by_id = AsyncMock(return_value=label)
    with pytest.raises(ValidationError):
        await service.assign_classification(
            uuid.uuid4(),
            AssignClassificationRequest(resource_id=uuid.uuid4(), label_id=label.id),
        )


@pytest.mark.asyncio
async def test_ensure_default_policy(
    service: ClassificationService, policy_repo: AsyncMock
) -> None:
    policy = await service.ensure_default_policy(uuid.uuid4())
    assert policy.name == "Default Classification Policy"
    policy_repo.upsert.assert_awaited_once()
