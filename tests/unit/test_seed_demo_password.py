"""Tests for demo seed password sourcing."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "seed_demo_data.py"
_SPEC = importlib.util.spec_from_file_location("seed_demo_data", _SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
_SEED = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_SEED)
resolve_demo_password = _SEED.resolve_demo_password


def test_resolve_demo_password_requires_env_when_not_dry_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="DEMO_PASSWORD"):
        resolve_demo_password(dry_run=False)


def test_resolve_demo_password_allows_unset_in_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    assert resolve_demo_password(dry_run=True) == ""


def test_resolve_demo_password_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_PASSWORD", "from-env-secret")
    assert resolve_demo_password(dry_run=False) == "from-env-secret"
