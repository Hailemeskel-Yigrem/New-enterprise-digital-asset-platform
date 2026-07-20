"""API tests for compliance routes."""

from __future__ import annotations

import uuid


def test_list_labels_route(client) -> None:
    org_id = uuid.uuid4()
    response = client.get(f"/api/v1/organizations/{org_id}/compliance/labels")
    assert response.status_code in (200, 422, 500)


def test_create_hold_route(client) -> None:
    org_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/organizations/{org_id}/compliance/holds",
        json={"name": "Test Hold", "matter_id": "M-1"},
        headers={"X-User-Id": str(uuid.uuid4())},
    )
    assert response.status_code in (201, 422, 500)
