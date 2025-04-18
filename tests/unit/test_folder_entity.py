"""Unit tests for folder entity behavior."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import ValidationError
from vaultforge.domain.assets.entities import Folder
from vaultforge.domain.assets.enums import FolderKind


def test_folder_rename_updates_name_and_timestamp() -> None:
    folder = Folder(name="Reports")
    original_updated = folder.updated_at
    folder.rename("  Finance  ")
    assert folder.name == "Finance"
    assert folder.updated_at >= original_updated


def test_folder_rename_rejects_empty_name() -> None:
    folder = Folder(name="Reports")
    with pytest.raises(ValidationError, match="Folder name cannot be empty"):
        folder.rename("   ")


def test_folder_move_rejects_self_reference() -> None:
    folder = Folder(name="Root")
    with pytest.raises(ValidationError, match="cannot be moved into itself"):
        folder.move(folder.id, descendant_ids=frozenset())


def test_folder_move_rejects_descendant_target() -> None:
    folder = Folder(name="Root")
    child_id = uuid.uuid4()
    with pytest.raises(ValidationError, match="descendants"):
        folder.move(child_id, descendant_ids=frozenset({child_id}))


def test_folder_move_allows_valid_parent() -> None:
    folder = Folder(name="Root", kind=FolderKind.ROOT)
    new_parent = uuid.uuid4()
    folder.move(new_parent, descendant_ids=frozenset())
    assert folder.parent_id == new_parent
