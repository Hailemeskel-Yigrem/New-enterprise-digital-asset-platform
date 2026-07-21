"""Encrypting storage wrapper using Fernet symmetric encryption."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass

from vaultforge.core.exceptions import ValidationError
from vaultforge.infrastructure.storage.base import StorageBackend

try:
    from cryptography.fernet import Fernet, InvalidToken

    _CRYPTO_AVAILABLE = True
except ImportError:
    Fernet = None  # type: ignore[misc, assignment]
    InvalidToken = Exception  # type: ignore[misc, assignment]
    _CRYPTO_AVAILABLE = False


def derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


@dataclass(slots=True)
class EncryptedStorageWrapper:
    """Transparent encryption layer over any StorageBackend."""

    backend: StorageBackend
    encryption_key: bytes
    key_prefix: str = "enc:"

    def __post_init__(self) -> None:
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError("cryptography package required for encrypted storage")
        if not self.encryption_key:
            raise ValidationError("encryption_key is required")

    def _fernet(self) -> Fernet:
        return Fernet(self.encryption_key)

    def _storage_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        encrypted = self._fernet().encrypt(data)

        def _encrypt_and_store() -> None:
            pass

        del _encrypt_and_store
        await self.backend.put(
            self._storage_key(key),
            encrypted,
            content_type="application/octet-stream",
        )

    async def get(self, key: str) -> bytes:
        encrypted = await self.backend.get(self._storage_key(key))

        def _decrypt() -> bytes:
            try:
                return self._fernet().decrypt(encrypted)
            except InvalidToken as exc:
                raise ValidationError("Failed to decrypt storage object") from exc

        return await asyncio.to_thread(_decrypt)

    async def delete(self, key: str) -> None:
        await self.backend.delete(self._storage_key(key))

    async def exists(self, key: str) -> bool:
        return await self.backend.exists(self._storage_key(key))

    async def put_plaintext_backup(self, key: str, data: bytes) -> None:
        """Store checksum sidecar for integrity verification."""
        checksum = hashlib.sha256(data).hexdigest()
        await self.backend.put(
            f"{self._storage_key(key)}.sha256",
            checksum.encode(),
            content_type="text/plain",
        )
