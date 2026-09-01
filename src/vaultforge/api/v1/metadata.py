"""Custom metadata API routes."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from vaultforge.application.assets.metadata_schemas import (
    MetadataSchemaCreateRequest,
    MetadataSchemaResponse,
    MetadataSchemaUpdateRequest,
    MetadataValueResponse,
    MetadataValueUpsertRequest,
)
from vaultforge.application.assets.metadata_service import MetadataService
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.metadata_repository import (
    SqlAlchemyMetadataSchemaRepository,
    SqlAlchemyMetadataValueRepository,
)
from vaultforge.infrastructure.persistence.session import get_db_session

router = APIRouter(prefix="/organizations/{organization_id}/metadata", tags=["metadata"])


def _resolve_user_id(x_user_id: str | None) -> uuid.UUID:
    if not x_user_id:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")
    return uuid.UUID(x_user_id)


def _http_error(exc: VaultForgeError) -> Exception:
    from fastapi import HTTPException

    code_map = {
        "not_found": status.HTTP_404_NOT_FOUND,
        "conflict": status.HTTP_409_CONFLICT,
        "validation_error": status.HTTP_422_UNPROCESSABLE_CONTENT,
        "forbidden": status.HTTP_403_FORBIDDEN,
    }
    return HTTPException(
        status_code=code_map.get(exc.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": exc.code, "message": exc.message},
    )


async def get_metadata_service(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncIterator[MetadataService]:
    yield MetadataService(
        SqlAlchemyMetadataSchemaRepository(session),
        SqlAlchemyMetadataValueRepository(session),
    )


@router.post("/schemas", response_model=MetadataSchemaResponse, status_code=status.HTTP_201_CREATED)
async def create_schema(
    organization_id: uuid.UUID,
    payload: MetadataSchemaCreateRequest,
    service: MetadataService = Depends(get_metadata_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> MetadataSchemaResponse:
    try:
        return await service.create_schema(organization_id, _resolve_user_id(x_user_id), payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get("/schemas", response_model=list[MetadataSchemaResponse])
async def list_schemas(
    organization_id: uuid.UUID,
    service: MetadataService = Depends(get_metadata_service),
) -> list[MetadataSchemaResponse]:
    return await service.list_schemas(organization_id)


@router.patch("/schemas/{schema_id}", response_model=MetadataSchemaResponse)
async def update_schema(
    organization_id: uuid.UUID,
    schema_id: uuid.UUID,
    payload: MetadataSchemaUpdateRequest,
    service: MetadataService = Depends(get_metadata_service),
) -> MetadataSchemaResponse:
    try:
        return await service.update_schema(organization_id, schema_id, payload)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.delete("/schemas/{schema_id}", response_model=MetadataSchemaResponse)
async def deactivate_schema(
    organization_id: uuid.UUID,
    schema_id: uuid.UUID,
    service: MetadataService = Depends(get_metadata_service),
) -> MetadataSchemaResponse:
    try:
        return await service.deactivate_schema(organization_id, schema_id)
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.put(
    "/schemas/{schema_id}/resources/{resource_type}/{resource_id}",
    response_model=MetadataValueResponse,
)
async def upsert_metadata_values(
    organization_id: uuid.UUID,
    schema_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    payload: MetadataValueUpsertRequest,
    service: MetadataService = Depends(get_metadata_service),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> MetadataValueResponse:
    try:
        return await service.upsert_values(
            organization_id,
            schema_id,
            resource_type,
            resource_id,
            _resolve_user_id(x_user_id),
            payload,
        )
    except VaultForgeError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/resources/{resource_type}/{resource_id}",
    response_model=MetadataValueResponse | None,
)
async def get_metadata_values(
    organization_id: uuid.UUID,
    resource_type: str,
    resource_id: uuid.UUID,
    service: MetadataService = Depends(get_metadata_service),
) -> MetadataValueResponse | None:
    return await service.get_values(organization_id, resource_type, resource_id)
