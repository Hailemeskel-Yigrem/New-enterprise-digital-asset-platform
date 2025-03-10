"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _test_env() -> None:
    os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-32chars-minimum!!")
    os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-32chars-min!!")
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("APP_DEBUG", "true")


@pytest.fixture
def client(_test_env: None):
    from vaultforge.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
