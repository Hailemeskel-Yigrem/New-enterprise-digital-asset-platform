"""Unit tests for encrypted storage wrapper."""

from __future__ import annotations

import pytest

from vaultforge.infrastructure.storage.encrypted import EncryptedStorageWrapper, derive_fernet_key
from vaultforge.infrastructure.storage.s3 import InMemoryS3Fallback

pytest.importorskip("cryptography")


@pytest.fixture
def encrypted_storage() -> EncryptedStorageWrapper:
    key = derive_fernet_key("test-secret-key-for-encryption")
    return EncryptedStorageWrapper(backend=InMemoryS3Fallback(), encryption_key=key)


@pytest.mark.asyncio
async def test_encrypt_decrypt_roundtrip(encrypted_storage: EncryptedStorageWrapper) -> None:
    await encrypted_storage.put("secret/doc", b"confidential data")
    data = await encrypted_storage.get("secret/doc")
    assert data == b"confidential data"


@pytest.mark.asyncio
async def test_encrypted_delete(encrypted_storage: EncryptedStorageWrapper) -> None:
    await encrypted_storage.put("k", b"v")
    await encrypted_storage.delete("k")
    assert await encrypted_storage.exists("k") is False


def test_derive_fernet_key_deterministic() -> None:
    k1 = derive_fernet_key("same")
    k2 = derive_fernet_key("same")
    assert k1 == k2
