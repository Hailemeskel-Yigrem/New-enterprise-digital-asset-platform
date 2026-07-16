"""Password hashing and verification using bcrypt via passlib."""

from __future__ import annotations

from passlib.context import CryptContext

_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _prepare_password(plain_password: str) -> str:
    # bcrypt only uses the first 72 bytes; truncate intentionally for compatibility
    return plain_password.encode("utf-8")[:72].decode("utf-8", errors="ignore")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    return _context.hash(_prepare_password(plain_password))


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return _context.verify(_prepare_password(plain_password), password_hash)
