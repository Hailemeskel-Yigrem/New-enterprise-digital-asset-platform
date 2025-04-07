"""Repository interfaces for asset aggregates."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from vaultforge.domain.assets.entities import Document, DocumentLock, DocumentVersion, Folder
from vaultforge.domain.assets.enums import DocumentStatus


@dataclass(frozen=True, slots=True)
class DocumentSearchCriteria:
    organization_id: uuid.UUID
    name: str | None = None
    status: DocumentStatus | None = None
    folder_id: uuid.UUID | None = None
    tags: frozenset[str] = frozenset()
    include_deleted: bool = False
    limit: int = 50
    offset: int = 0


class FolderRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, folder_id: uuid.UUID
    ) -> Folder | None: ...

    @abstractmethod
    async def get_by_name_and_parent(
        self,
        organization_id: uuid.UUID,
        name: str,
        parent_id: uuid.UUID | None,
    ) -> Folder | None: ...

    @abstractmethod
    async def add(self, folder: Folder) -> Folder: ...

    @abstractmethod
    async def update(self, folder: Folder) -> Folder: ...

    @abstractmethod
    async def list_children(
        self,
        organization_id: uuid.UUID,
        parent_id: uuid.UUID | None,
    ) -> Sequence[Folder]: ...

    @abstractmethod
    async def list_descendant_ids(
        self, organization_id: uuid.UUID, folder_id: uuid.UUID
    ) -> frozenset[uuid.UUID]: ...


class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, organization_id: uuid.UUID, document_id: uuid.UUID
    ) -> Document | None: ...

    @abstractmethod
    async def add(self, document: Document) -> Document: ...

    @abstractmethod
    async def update(self, document: Document) -> Document: ...

    @abstractmethod
    async def search(self, criteria: DocumentSearchCriteria) -> Sequence[Document]: ...


class DocumentVersionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, version_id: uuid.UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def get_latest(self, document_id: uuid.UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def add(self, version: DocumentVersion) -> DocumentVersion: ...

    @abstractmethod
    async def update(self, version: DocumentVersion) -> DocumentVersion: ...

    @abstractmethod
    async def list_for_document(self, document_id: uuid.UUID) -> Sequence[DocumentVersion]: ...


class DocumentLockRepository(ABC):
    @abstractmethod
    async def get_active_for_document(self, document_id: uuid.UUID) -> DocumentLock | None: ...

    @abstractmethod
    async def add(self, lock: DocumentLock) -> DocumentLock: ...

    @abstractmethod
    async def delete(self, lock_id: uuid.UUID) -> None: ...
