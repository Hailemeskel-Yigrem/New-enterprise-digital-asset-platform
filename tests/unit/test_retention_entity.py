"""Unit tests for retention domain entities."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.common import utc_now
from vaultforge.domain.retention.entities import LegalHold, RetentionPolicy, RetentionSchedule
from vaultforge.domain.retention.enums import (
    LegalHoldStatus,
    RetentionScope,
)


def test_retention_policy_requires_name() -> None:
    with pytest.raises(ValidationError):
        RetentionPolicy(name="")


def test_retention_policy_scoped_requires_ref() -> None:
    with pytest.raises(ValidationError):
        RetentionPolicy(name="Folder policy", scope=RetentionScope.FOLDER)


def test_retention_policy_compute_expiry() -> None:
    policy = RetentionPolicy(name="Default", retention_days=30)
    reference = utc_now()
    expiry = policy.compute_expiry(reference)
    assert expiry >= reference + timedelta(days=29)


def test_retention_schedule_is_due() -> None:
    schedule = RetentionSchedule(expires_at=utc_now() - timedelta(days=1))
    assert schedule.is_due()


def test_retention_schedule_blocked_by_hold() -> None:
    schedule = RetentionSchedule(
        expires_at=utc_now() - timedelta(days=1),
        blocked_by_legal_hold=True,
    )
    assert not schedule.is_due()


def test_legal_hold_covers_resource() -> None:
    resource_id = uuid.uuid4()
    hold = LegalHold(name="Matter A", resource_ids=[resource_id])
    assert hold.covers_resource(resource_id)


def test_legal_hold_release() -> None:
    actor = uuid.uuid4()
    hold = LegalHold(name="Matter B")
    hold.release(actor)
    assert hold.status == LegalHoldStatus.RELEASED
    assert hold.released_by == actor
