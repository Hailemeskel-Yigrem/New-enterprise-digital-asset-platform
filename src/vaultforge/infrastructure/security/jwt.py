"""JWT access and refresh token creation and validation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from vaultforge.core.config import Settings, get_settings
from vaultforge.core.exceptions import AuthenticationError

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _now() -> datetime:
    return datetime.now(UTC)


def create_access_token(
    user_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token for the given user."""
    cfg = settings or get_settings()
    expire = _now() + (
        expires_delta or timedelta(minutes=cfg.jwt_access_token_expire_minutes)
    )
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_ACCESS,
        "exp": expire,
        "iat": _now(),
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def create_refresh_token(
    user_id: uuid.UUID,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token for the given user."""
    cfg = settings or get_settings()
    expire = _now() + (
        expires_delta or timedelta(days=cfg.jwt_refresh_token_expire_days)
    )
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_REFRESH,
        "exp": expire,
        "iat": _now(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, cfg.jwt_secret_key, algorithm=cfg.jwt_algorithm)


def decode_token(
    token: str,
    *,
    expected_type: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Decode and validate a JWT, optionally enforcing token type."""
    cfg = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            cfg.jwt_secret_key,
            algorithms=[cfg.jwt_algorithm],
        )
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthenticationError("Invalid token type")

    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError("Token missing subject")

    return payload


def get_user_id_from_token(
    token: str,
    *,
    expected_type: str | None = None,
    settings: Settings | None = None,
) -> uuid.UUID:
    """Extract the user UUID from a validated JWT."""
    payload = decode_token(token, expected_type=expected_type, settings=settings)
    try:
        return uuid.UUID(str(payload["sub"]))
    except (ValueError, TypeError) as exc:
        raise AuthenticationError("Invalid token subject") from exc
