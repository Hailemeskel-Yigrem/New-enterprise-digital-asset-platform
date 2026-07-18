"""Unit tests for domain events."""

from __future__ import annotations

import uuid

from vaultforge.domain.events import (
    DomainEvent,
    EventTypes,
    document_created,
    metadata_updated,
    quota_exceeded,
)


def test_domain_event_to_dict_roundtrip() -> None:
    org_id = uuid.uuid4()
    event = document_created(org_id, uuid.uuid4(), name="test.pdf")
    data = event.to_dict()
    restored = DomainEvent.from_dict(data)
    assert restored.event_type == EventTypes.DOCUMENT_CREATED
    assert restored.organization_id == org_id


def test_metadata_updated_event() -> None:
    event = metadata_updated(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
    assert event.event_type == EventTypes.METADATA_UPDATED


def test_quota_exceeded_event_payload() -> None:
    event = quota_exceeded(uuid.uuid4(), "storage_bytes", 2000, 1000)
    assert event.payload["consumed"] == 2000
