"""Document preview and thumbnail generation."""

from __future__ import annotations

import io
import uuid
from dataclasses import dataclass
from typing import cast

from pydantic import BaseModel

from vaultforge.core.exceptions import NotFoundError
from vaultforge.domain.assets.repositories import DocumentRepository, DocumentVersionRepository
from vaultforge.infrastructure.storage.base import StorageBackend


class PreviewMetadata(BaseModel):
    document_id: uuid.UUID
    version_id: uuid.UUID
    content_type: str
    width: int | None = None
    height: int | None = None
    page_count: int | None = None
    thumbnail_available: bool = False


@dataclass(slots=True)
class PreviewService:
    documents: DocumentRepository
    versions: DocumentVersionRepository
    storage: StorageBackend

    async def get_metadata(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
    ) -> PreviewMetadata:
        document = await self.documents.get_by_id(organization_id, document_id)
        if document is None or document.current_version_id is None:
            raise NotFoundError("Document or version not found")

        version = await self.versions.get_by_id(document.current_version_id)
        if version is None:
            raise NotFoundError("Document version not found")

        metadata = PreviewMetadata(
            document_id=document.id,
            version_id=version.id,
            content_type=version.content_type,
        )
        if version.content_type == "application/pdf":
            metadata.page_count = None
            return metadata

        if version.content_type.startswith("image/"):
            try:
                content = await self.storage.get(version.storage_key)
                width, height = self._image_dimensions(content)
                metadata.width = width
                metadata.height = height
                metadata.thumbnail_available = True
            except Exception:
                metadata.thumbnail_available = False
        return metadata

    async def generate_thumbnail(
        self,
        organization_id: uuid.UUID,
        document_id: uuid.UUID,
        *,
        max_size: tuple[int, int] = (256, 256),
    ) -> bytes | None:
        document = await self.documents.get_by_id(organization_id, document_id)
        if document is None or document.current_version_id is None:
            raise NotFoundError("Document or version not found")

        version = await self.versions.get_by_id(document.current_version_id)
        if version is None or not version.content_type.startswith("image/"):
            return None

        content = await self.storage.get(version.storage_key)
        return self._render_thumbnail(content, max_size)

    @staticmethod
    def _image_dimensions(content: bytes) -> tuple[int, int]:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            return cast(tuple[int, int], image.size)

    @staticmethod
    def _render_thumbnail(content: bytes, max_size: tuple[int, int]) -> bytes:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as image:
            image = image.convert("RGBA") if image.mode in {"P", "RGBA"} else image.convert("RGB")
            image.thumbnail(max_size)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            return buffer.getvalue()
