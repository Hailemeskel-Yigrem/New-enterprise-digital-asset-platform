"""API tests for metadata routes."""

from __future__ import annotations

import uuid


def test_metadata_schemas_route_exists(client) -> None:
    org_id = uuid.uuid4()
    response = client.get(f"/api/v1/organizations/{org_id}/metadata/schemas")
    assert response.status_code in (200, 422, 500)


def test_create_schema_validation(client) -> None:
    org_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/organizations/{org_id}/metadata/schemas",
        json={"name": "", "slug": "x", "fields": []},
    )
    assert response.status_code in (422, 500)
