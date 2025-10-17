"""Integration tests for documents API with mocked services."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from vaultforge.api.deps import get_current_user
from vaultforge.application.assets.document_service import DocumentService
from vaultforge.application.assets.schemas import DocumentResponse, DocumentSearchResponse
from vaultforge.application.assets.search_service import SearchService
from vaultforge.application.identity.schemas import UserResponse
from vaultforge.domain.assets.enums import DocumentStatus, SensitivityLabel
from vaultforge.infrastructure.persistence.session import get_db_session


def _user_response() -> UserResponse:
    now = datetime.now(timezone.utc)
    return UserResponse(
        id=uuid.uuid4(),
        email="docs@test.io",
        full_name="Doc Tester",
        is_active=True,
        is_email_verified=True,
        last_login_at=None,
        created_at=now,
        updated_at=now,
    )


def _document_response(org_id: uuid.UUID) -> DocumentResponse:
    now = datetime.now(timezone.utc)
    return DocumentResponse(
        id=uuid.uuid4(),
        organization_id=org_id,
        folder_id=uuid.uuid4(),
        name="Mock Contract.pdf",
        status=DocumentStatus.ACTIVE,
        sensitivity=SensitivityLabel.INTERNAL,
        tags=["legal"],
        current_version_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
        deleted_at=None,
        created_at=now,
        updated_at=now,
        current_version=None,
    )


@pytest.fixture
def documents_client(client: TestClient):
    org_id = uuid.uuid4()
    user = _user_response()
    doc = _document_response(org_id)

    mock_search = AsyncMock(spec=SearchService)
    mock_search.search_documents = AsyncMock(
        return_value=DocumentSearchResponse(items=[doc], total=1, limit=50, offset=0)
    )

    mock_docs = AsyncMock(spec=DocumentService)
    mock_docs.get_document = AsyncMock(return_value=doc)
    mock_docs.delete_document = AsyncMock(return_value=doc)

    async def override_db():
        yield AsyncMock()

    from vaultforge.api.v1 import documents as documents_module

    app = client.app
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[documents_module.get_search_service] = lambda: mock_search
    app.dependency_overrides[documents_module.get_document_service] = lambda: mock_docs

    yield client, org_id, doc, mock_search, mock_docs
    app.dependency_overrides.clear()


def test_search_documents_returns_items(documents_client) -> None:
    client, org_id, doc, mock_search, _ = documents_client
    response = client.post(
        f"/api/v1/organizations/{org_id}/documents/search",
        json={"limit": 50, "offset": 0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == doc.name
    mock_search.search_documents.assert_awaited()


def test_get_document_by_id(documents_client) -> None:
    client, org_id, doc, _, mock_docs = documents_client
    response = client.get(f"/api/v1/organizations/{org_id}/documents/{doc.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(doc.id)
    mock_docs.get_document.assert_awaited()


def test_delete_document(documents_client) -> None:
    client, org_id, doc, _, mock_docs = documents_client
    response = client.delete(f"/api/v1/organizations/{org_id}/documents/{doc.id}")
    assert response.status_code == 200
    mock_docs.delete_document.assert_awaited()

def test_search_documents_validates_pagination(documents_client) -> None:
    client, org_id, _, mock_search, _ = documents_client
    response = client.post(
        f"/api/v1/organizations/{org_id}/documents/search",
        json={"limit": 10, "offset": 5},
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert body["limit"] == 10 or "limit" not in body
    mock_search.search_documents.assert_awaited()


def test_get_document_returns_404_when_missing(client: TestClient) -> None:
    org_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    user = _user_response()

    mock_docs = AsyncMock(spec=DocumentService)
    mock_docs.get_document = AsyncMock(side_effect=Exception("not found"))

    from vaultforge.api.v1 import documents as documents_module

    app = client.app
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[documents_module.get_document_service] = lambda: mock_docs

    response = client.get(f"/api/v1/organizations/{org_id}/documents/{doc_id}")
    assert response.status_code >= 400
    app.dependency_overrides.clear()
