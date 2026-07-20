"""Unit tests for compliance domain entities."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.compliance.entities import (
    ClassificationLabel,
    ClassificationPolicy,
    ComplianceHold,
    ExportManifest,
    ExportPackage,
)
from vaultforge.domain.compliance.enums import (
    ClassificationLevel,
    ComplianceHoldStatus,
    ExportStatus,
)


def test_classification_label_requires_name() -> None:
    with pytest.raises(ValidationError):
        ClassificationLabel(name="")


def test_policy_blocks_downgrade() -> None:
    policy = ClassificationPolicy(block_downgrade=True)
    assert not policy.is_transition_allowed(
        ClassificationLevel.CONFIDENTIAL,
        ClassificationLevel.PUBLIC,
    )


def test_hold_covers_resource() -> None:
    resource_id = uuid.uuid4()
    hold = ComplianceHold(name="Hold", resource_ids=[resource_id])
    assert hold.covers_resource(resource_id)


def test_hold_release() -> None:
    hold = ComplianceHold(name="Hold")
    actor = uuid.uuid4()
    hold.release(actor)
    assert hold.status == ComplianceHoldStatus.RELEASED
    assert hold.released_by == actor


def test_export_manifest_finalize() -> None:
    manifest = ExportManifest()
    manifest.add_entry(uuid.uuid4(), "file.pdf", 100, "key")
    checksum = manifest.finalize()
    assert len(checksum) == 64


def test_export_package_completed() -> None:
    package = ExportPackage()
    package.mark_completed("exports/test.zip")
    assert package.status == ExportStatus.COMPLETED
    assert package.storage_key == "exports/test.zip"
