"""Unit tests for JWT helpers."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import AuthenticationError
from vaultforge.infrastructure.security.jwt import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
)


def test_create_and_decode_access_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    payload = decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == TOKEN_TYPE_ACCESS


def test_create_and_decode_refresh_token() -> None:
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    payload = decode_token(token, expected_type=TOKEN_TYPE_REFRESH)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == TOKEN_TYPE_REFRESH
    assert "jti" in payload


def test_get_user_id_from_token() -> None:
    user_id = uuid.uuid4()
    token = create_access_token(user_id)
    assert get_user_id_from_token(token, expected_type=TOKEN_TYPE_ACCESS) == user_id


def test_wrong_token_type_raises() -> None:
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    with pytest.raises(AuthenticationError):
        decode_token(token, expected_type=TOKEN_TYPE_ACCESS)
