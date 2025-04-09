"""Blob storage backends."""

from vaultforge.infrastructure.storage.base import StorageBackend, StorageObject
from vaultforge.infrastructure.storage.local import LocalFilesystemStorage

__all__ = ["StorageBackend", "StorageObject", "LocalFilesystemStorage"]
