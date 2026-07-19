"""Validation helpers for bulk asset operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from vaultforge.core.exceptions import ValidationError

MAX_BULK_ITEMS = 1000
MAX_TAG_LENGTH = 64


@dataclass(frozen=True, slots=True)
class BulkValidationResult:
    valid_ids: list[uuid.UUID]
    invalid_ids: list[uuid.UUID]
    messages: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.invalid_ids


def validate_bulk_item_count(count: int, *, max_items: int = MAX_BULK_ITEMS) -> None:
    if count < 1:
        raise ValidationError("Bulk operation requires at least one item")
    if count > max_items:
        raise ValidationError(f"Bulk operation exceeds maximum of {max_items} items")


def validate_resource_ids(resource_ids: list[uuid.UUID]) -> BulkValidationResult:
    valid: list[uuid.UUID] = []
    invalid: list[uuid.UUID] = []
    messages: dict[str, str] = {}
    seen: set[uuid.UUID] = set()
    for rid in resource_ids:
        key = str(rid)
        if rid in seen:
            invalid.append(rid)
            messages[key] = "duplicate resource id"
            continue
        seen.add(rid)
        if rid.int == 0:
            invalid.append(rid)
            messages[key] = "invalid nil uuid"
            continue
        valid.append(rid)
    return BulkValidationResult(valid_ids=valid, invalid_ids=invalid, messages=messages)


def normalize_tags(tags: set[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        cleaned = tag.strip().lower()
        if not cleaned:
            continue
        if len(cleaned) > MAX_TAG_LENGTH:
            raise ValidationError(f"Tag exceeds max length: {cleaned[:20]}")
        if cleaned not in normalized:
            normalized.append(cleaned)
    if len(normalized) > 50:
        raise ValidationError("Maximum 50 tags per document")
    return sorted(normalized)


def validate_move_target(
    source_folder_id: uuid.UUID | None,
    target_folder_id: uuid.UUID | None,
    descendant_ids: frozenset[uuid.UUID],
) -> None:
    if target_folder_id is None:
        return
    if target_folder_id == source_folder_id:
        raise ValidationError("Document already in target folder")
    if target_folder_id in descendant_ids:
        raise ValidationError("Cannot move into descendant folder")
