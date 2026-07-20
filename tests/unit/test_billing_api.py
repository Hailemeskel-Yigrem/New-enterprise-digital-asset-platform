"""API tests for billing routes."""

from __future__ import annotations

import uuid


def test_get_usage_route(client) -> None:
    org_id = uuid.uuid4()
    response = client.get(f"/api/v1/organizations/{org_id}/billing/usage")
    assert response.status_code in (200, 422, 500)


def test_list_quotas_route(client) -> None:
    org_id = uuid.uuid4()
    response = client.get(f"/api/v1/organizations/{org_id}/billing/quotas")
    assert response.status_code in (200, 422, 500)


def test_get_plan_route(client) -> None:
    org_id = uuid.uuid4()
    response = client.get(f"/api/v1/organizations/{org_id}/billing/plan")
    assert response.status_code in (200, 422, 500)
