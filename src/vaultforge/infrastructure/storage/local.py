"""Local filesystem blob storage."""

from __future__ import annotations

import asyncio
from pathlib import Path

from vaultforge.core.exceptions import NotFoundError, ValidationError


class LocalFilesystemStorage:
    """Store blobs under a base directory keyed by storage path."""

    def __init__(self, base_path: str | Path) -> None:
        self._base_path = Path(base_path).resolve()
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_key(self, key: str) -> Path:
        normalized = key.replace("\\", "/").lstrip("/")
        if not normalized or ".." in normalized.split("/"):
            raise ValidationError("Invalid storage key")
        target = (self._base_path / normalized).resolve()
        if not str(target).startswith(str(self._base_path)):
            raise ValidationError("Invalid storage key")
        return target

    async def put(
        self,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        del content_type  # metadata not persisted on local filesystem
        target = self._resolve_key(key)

        def _write() -> None:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        await asyncio.to_thread(_write)

    async def get(self, key: str) -> bytes:
        target = self._resolve_key(key)

        def _read() -> bytes:
            if not target.is_file():
                raise NotFoundError(f"Storage object not found: {key}")
            return target.read_bytes()

        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        target = self._resolve_key(key)

        def _delete() -> None:
            if target.is_file():
                target.unlink()

        await asyncio.to_thread(_delete)

    async def exists(self, key: str) -> bool:
        target = self._resolve_key(key)
        return await asyncio.to_thread(target.is_file)
