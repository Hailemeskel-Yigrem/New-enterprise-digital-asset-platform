"""Unit tests for local filesystem storage backend."""

from __future__ import annotations

import pytest

from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage


@pytest.fixture
def storage(tmp_path) -> LocalFilesystemStorage:
    return LocalFilesystemStorage(tmp_path)


@pytest.mark.asyncio
async def test_put_get_roundtrip(storage: LocalFilesystemStorage) -> None:
    await storage.put("org/doc/v1/file.txt", b"hello", content_type="text/plain")
    assert await storage.get("org/doc/v1/file.txt") == b"hello"


@pytest.mark.asyncio
async def test_exists_and_delete(storage: LocalFilesystemStorage) -> None:
    key = "org/doc/v1/remove.bin"
    assert await storage.exists(key) is False
    await storage.put(key, b"payload")
    assert await storage.exists(key) is True
    await storage.delete(key)
    assert await storage.exists(key) is False


@pytest.mark.asyncio
async def test_get_missing_raises_not_found(storage: LocalFilesystemStorage) -> None:
    with pytest.raises(NotFoundError):
        await storage.get("missing/object")


@pytest.mark.asyncio
async def test_rejects_path_traversal(storage: LocalFilesystemStorage) -> None:
    with pytest.raises(ValidationError):
        await storage.put("../escape.txt", b"nope")
