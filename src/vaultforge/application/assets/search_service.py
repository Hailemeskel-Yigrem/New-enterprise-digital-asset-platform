"""Document search application service."""

from __future__ import annotations

import uuid

from vaultforge.application.assets.schemas import (
    DocumentResponse,
    DocumentSearchRequest,
    DocumentSearchResponse,
    DocumentVersionResponse,
)
from vaultforge.domain.assets.repositories import (
    DocumentRepository,
    DocumentSearchCriteria,
    DocumentVersionRepository,
)


class SearchService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        version_repo: DocumentVersionRepository,
    ) -> None:
        self._documents = document_repo
        self._versions = version_repo

    async def search_documents(
        self,
        organization_id: uuid.UUID,
        payload: DocumentSearchRequest,
    ) -> DocumentSearchResponse:
        criteria = DocumentSearchCriteria(
            organization_id=organization_id,
            name=payload.name,
            status=payload.status,
            folder_id=payload.folder_id,
            tags=frozenset(tag.strip().lower() for tag in payload.tags if tag.strip()),
            include_deleted=payload.include_deleted,
            limit=payload.limit,
            offset=payload.offset,
        )
        documents = await self._documents.search(criteria)
        items: list[DocumentResponse] = []
        for document in documents:
            version = None
            if document.current_version_id is not None:
                version = await self._versions.get_by_id(document.current_version_id)
            version_response = (
                DocumentVersionResponse.model_validate(version) if version is not None else None
            )
            items.append(
                DocumentResponse(
                    id=document.id,
                    organization_id=document.organization_id,
                    folder_id=document.folder_id,
                    name=document.name,
                    status=document.status,
                    sensitivity=document.sensitivity,
                    tags=document.tags,
                    current_version_id=document.current_version_id,
                    created_by=document.created_by,
                    deleted_at=document.deleted_at,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    current_version=version_response,
                )
            )
        return DocumentSearchResponse(
            items=items,
            total=len(items),
            limit=payload.limit,
            offset=payload.offset,
        )
