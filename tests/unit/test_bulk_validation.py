"""Unit tests for bulk validation helpers."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.application.assets.bulk_validation import (
    normalize_tags,
    validate_bulk_item_count,
    validate_move_target,
    validate_resource_ids,
)
from vaultforge.core.exceptions import ValidationError


def test_validate_bulk_item_count_ok() -> None:
    validate_bulk_item_count(10)


def test_validate_bulk_item_count_too_many() -> None:
    with pytest.raises(ValidationError):
        validate_bulk_item_count(5000)


def test_validate_resource_ids_deduplicates() -> None:
    rid = uuid.uuid4()
    result = validate_resource_ids([rid, rid])
    assert result.invalid_ids == [rid]


def test_normalize_tags() -> None:
    assert normalize_tags({"Alpha", "beta", "ALPHA"}) == ["alpha", "beta"]


def test_validate_move_target_descendant() -> None:
    parent = uuid.uuid4()
    child = uuid.uuid4()
    with pytest.raises(ValidationError):
        validate_move_target(parent, child, frozenset({child}))
