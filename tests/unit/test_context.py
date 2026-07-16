"""Unit tests for request context variables."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.context import (
    bind_context,
    clear_context,
    get_org_id,
    get_request_id,
    get_user_id,
    reset_request_id,
    set_org_id,
    set_request_id,
    set_user_id,
)


@pytest.fixture(autouse=True)
def _clean_context() -> None:
    clear_context()


def test_set_and_get_context_values() -> None:
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()
    request_id = "req-abc-123"

    set_org_id(org_id)
    set_user_id(user_id)
    set_request_id(request_id)

    assert get_org_id() == org_id
    assert get_user_id() == user_id
    assert get_request_id() == request_id


def test_reset_context_restores_prior_value() -> None:
    set_request_id("first")
    token = set_request_id("second")
    assert get_request_id() == "second"

    reset_request_id(token)
    assert get_request_id() == "first"


def test_clear_context_resets_all() -> None:
    set_org_id(uuid.uuid4())
    set_user_id(uuid.uuid4())
    set_request_id("rid")

    clear_context()

    assert get_org_id() is None
    assert get_user_id() is None
    assert get_request_id() is None


def test_bind_context_sets_and_restores() -> None:
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    with bind_context(org_id=org_id, user_id=user_id, request_id="bound-req"):
        assert get_org_id() == org_id
        assert get_user_id() == user_id
        assert get_request_id() == "bound-req"

    assert get_org_id() is None
    assert get_user_id() is None
    assert get_request_id() is None
