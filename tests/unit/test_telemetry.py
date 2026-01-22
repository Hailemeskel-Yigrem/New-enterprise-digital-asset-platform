"""Unit tests for core telemetry helpers."""

from __future__ import annotations

from vaultforge.api.monitoring import snapshot_counters
from vaultforge.core.telemetry import observe_duration, record_metric, timed_operation


def test_record_metric_increments_counter() -> None:
    before = snapshot_counters().get("unit_test_event", 0)
    record_metric("unit_test_event", 2)
    after = snapshot_counters().get("unit_test_event", 0)
    assert after == before + 2


def test_timed_operation_records_duration_and_count() -> None:
    with timed_operation("unit_test_op"):
        pass

    counters = snapshot_counters()
    assert counters.get("unit_test_op_count", 0) >= 1
    assert counters.get("unit_test_op_duration_ms_total", 0) >= 0


def test_timed_operation_records_labels() -> None:
    with timed_operation("unit_test_labeled", status="ok"):
        pass

    counters = snapshot_counters()
    assert counters.get("unit_test_labeled_status_ok_count", 0) >= 1


def test_observe_duration_records_values() -> None:
    observe_duration("unit_test_observe", 42.5)
    counters = snapshot_counters()
    assert counters.get("unit_test_observe_count", 0) >= 1
    assert counters.get("unit_test_observe_duration_ms_total", 0) >= 42
