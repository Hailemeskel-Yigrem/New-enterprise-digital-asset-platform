"""Unit tests for dashboard metrics service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from vaultforge.application.analytics.dashboard_service import DashboardService


@pytest.mark.asyncio
async def test_get_dashboard_aggregates_counts() -> None:
    organization_id = uuid.uuid4()
    session = AsyncMock()

    org = SimpleNamespace(max_storage_gb=10)
    session.get = AsyncMock(return_value=org)

    scalar_values = iter([5, 3, 2, 1024])
    execute_result = MagicMock()

    def configure_execute(result):
        execute_result.scalars.return_value.all.return_value = result
        return execute_result

    documents = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name="Policy.pdf",
            created_by=uuid.uuid4(),
            updated_at=datetime.now(tz=UTC),
        )
    ]
    folders = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name="Legal",
            updated_at=datetime.now(tz=UTC),
        )
    ]

    async def execute_side_effect(stmt):
        sql = str(stmt)
        if "count" in sql.lower():
            result = MagicMock()
            result.scalar_one.return_value = next(scalar_values)
            return result
        if "sum" in sql.lower():
            result = MagicMock()
            result.scalar_one.return_value = next(scalar_values)
            return result
        if "documents" in sql.lower():
            return configure_execute(documents)
        return configure_execute(folders)

    session.execute = AsyncMock(side_effect=execute_side_effect)

    service = DashboardService(session)
    dashboard = await service.get_dashboard(organization_id)

    assert dashboard.stats.document_count == 5
    assert dashboard.stats.folder_count == 3
    assert dashboard.stats.pending_approvals == 2
    assert dashboard.stats.storage_used_bytes == 1024
    assert dashboard.stats.storage_limit_bytes == 10 * 1024 * 1024 * 1024
    assert dashboard.recent_activity
