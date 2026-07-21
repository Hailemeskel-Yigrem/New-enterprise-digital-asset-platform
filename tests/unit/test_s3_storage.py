"""Unit tests for S3 storage backend."""

from __future__ import annotations

import pytest

from vaultforge.core.exceptions import NotFoundError, ValidationError
from vaultforge.infrastructure.storage.s3 import (
    InMemoryS3Fallback,
    S3StorageConfig,
    create_s3_backend,
)


@pytest.mark.asyncio
async def test_in_memory_fallback_put_get() -> None:
    storage = InMemoryS3Fallback()
    await storage.put("test/key", b"hello")
    data = await storage.get("test/key")
    assert data == b"hello"


@pytest.mark.asyncio
async def test_in_memory_fallback_not_found() -> None:
    storage = InMemoryS3Fallback()
    with pytest.raises(NotFoundError):
        await storage.get("missing")


@pytest.mark.asyncio
async def test_in_memory_fallback_exists() -> None:
    storage = InMemoryS3Fallback()
    await storage.put("k", b"x")
    assert await storage.exists("k") is True
    assert await storage.exists("missing") is False


def test_s3_config_requires_bucket() -> None:
    with pytest.raises(ValidationError):
        S3StorageConfig(bucket="")


def test_create_s3_backend_without_boto3() -> None:
    backend = create_s3_backend(S3StorageConfig(bucket="test"))
    assert isinstance(backend, InMemoryS3Fallback)
