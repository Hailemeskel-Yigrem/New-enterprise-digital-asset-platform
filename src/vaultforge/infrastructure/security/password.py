"""Password hashing and verification using bcrypt via passlib."""

from __future__ import annotations

from passlib.context import CryptContext

_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    return _context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return _context.verify(plain_password, password_hash)
