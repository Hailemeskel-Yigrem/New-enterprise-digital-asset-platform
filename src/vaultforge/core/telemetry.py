"""Simple timing and metrics helpers for VaultForge."""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from vaultforge.api.monitoring import increment_counter


@contextmanager
def timed_operation(name: str, **labels: Any) -> Generator[None, None, None]:
    """Measure elapsed milliseconds and increment Prometheus-style counters."""
    started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        increment_counter(f"{name}_duration_ms_total", int(elapsed_ms))
        increment_counter(f"{name}_count", 1)
        for key, value in labels.items():
            if value is not None:
                increment_counter(f"{name}_{key}_{value}_count", 1)


def record_metric(name: str, amount: int = 1) -> None:
    """Increment a named counter by the given amount."""
    increment_counter(name, amount)


def observe_duration(name: str, duration_ms: float) -> None:
    """Record a pre-computed duration in milliseconds."""
    increment_counter(f"{name}_duration_ms_total", int(duration_ms))
    increment_counter(f"{name}_count", 1)
