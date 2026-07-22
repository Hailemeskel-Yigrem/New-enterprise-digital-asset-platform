"""Request-scoped context variables for org, user, and request correlation."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

_org_id: ContextVar[uuid.UUID | None] = ContextVar("org_id", default=None)
_user_id: ContextVar[uuid.UUID | None] = ContextVar("user_id", default=None)
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_org_id() -> uuid.UUID | None:
    return _org_id.get()


def set_org_id(org_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    return _org_id.set(org_id)


def get_user_id() -> uuid.UUID | None:
    return _user_id.get()


def set_user_id(user_id: uuid.UUID | None) -> Token[uuid.UUID | None]:
    return _user_id.set(user_id)


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(request_id: str | None) -> Token[str | None]:
    return _request_id.set(request_id)


def reset_org_id(token: Token[uuid.UUID | None]) -> None:
    _org_id.reset(token)


def reset_user_id(token: Token[uuid.UUID | None]) -> None:
    _user_id.reset(token)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id.reset(token)


def clear_context() -> None:
    """Clear all context variables (typically in test teardown)."""
    _org_id.set(None)
    _user_id.set(None)
    _request_id.set(None)


@contextmanager
def bind_context(
    *,
    org_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> Generator[None, None, None]:
    """Temporarily bind org/user/request IDs for the current async context."""
    tokens: list[tuple[ContextVar[Any], Token[Any]]] = []
    if org_id is not None:
        tokens.append((_org_id, set_org_id(org_id)))
    if user_id is not None:
        tokens.append((_user_id, set_user_id(user_id)))
    if request_id is not None:
        tokens.append((_request_id, set_request_id(request_id)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)
