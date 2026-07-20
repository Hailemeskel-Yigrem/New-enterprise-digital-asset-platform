"""Storage and seat usage metering service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from vaultforge.application.billing.schemas import UsageSnapshotResponse
from vaultforge.domain.billing.entities import UsageRecord, UsageSnapshot
from vaultforge.domain.billing.enums import QuotaMetric, UsageEventType
from vaultforge.domain.billing.repositories import UsageRecordRepository, UsageSnapshotRepository
from vaultforge.domain.common import utc_now


@dataclass(slots=True)
class UsageMeter:
    records: UsageRecordRepository
    snapshots: UsageSnapshotRepository
    _seat_counts: dict[uuid.UUID, int] = field(default_factory=dict)

    async def record_storage_delta(
        self,
        organization_id: uuid.UUID,
        delta_bytes: int,
        *,
        resource_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> UsageSnapshotResponse:
        record = UsageRecord(
            organization_id=organization_id,
            metric=QuotaMetric.STORAGE_BYTES,
            event_type=UsageEventType.STORAGE_DELTA,
            delta=delta_bytes,
            resource_id=resource_id,
            actor_id=actor_id,
        )
        await self.records.append(record)
        snapshot = await self._current_snapshot(organization_id)
        snapshot.increment(QuotaMetric.STORAGE_BYTES, delta_bytes)
        saved = await self.snapshots.upsert(snapshot)
        return UsageSnapshotResponse.model_validate(saved)

    async def assign_seat(self, organization_id: uuid.UUID) -> UsageSnapshotResponse:
        current = self._seat_counts.get(organization_id, 0)
        self._seat_counts[organization_id] = current + 1
        record = UsageRecord(
            organization_id=organization_id,
            metric=QuotaMetric.SEATS,
            event_type=UsageEventType.SEAT_ASSIGNED,
            absolute_value=self._seat_counts[organization_id],
        )
        await self.records.append(record)
        snapshot = await self._current_snapshot(organization_id)
        snapshot.set_total(QuotaMetric.SEATS, self._seat_counts[organization_id])
        saved = await self.snapshots.upsert(snapshot)
        return UsageSnapshotResponse.model_validate(saved)

    async def release_seat(self, organization_id: uuid.UUID) -> UsageSnapshotResponse:
        current = max(0, self._seat_counts.get(organization_id, 0) - 1)
        self._seat_counts[organization_id] = current
        record = UsageRecord(
            organization_id=organization_id,
            metric=QuotaMetric.SEATS,
            event_type=UsageEventType.SEAT_RELEASED,
            absolute_value=current,
        )
        await self.records.append(record)
        snapshot = await self._current_snapshot(organization_id)
        snapshot.set_total(QuotaMetric.SEATS, current)
        saved = await self.snapshots.upsert(snapshot)
        return UsageSnapshotResponse.model_validate(saved)

    async def get_snapshot(self, organization_id: uuid.UUID) -> UsageSnapshotResponse:
        snapshot = await self._current_snapshot(organization_id)
        return UsageSnapshotResponse.model_validate(snapshot)

    async def _current_snapshot(self, organization_id: uuid.UUID) -> UsageSnapshot:
        existing = await self.snapshots.get_current(organization_id)
        if existing is not None:
            return existing
        now = utc_now()
        return UsageSnapshot(organization_id=organization_id, period_start=now, period_end=now)
