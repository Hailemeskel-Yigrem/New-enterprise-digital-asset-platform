"""Unit tests for password hashing."""

from __future__ import annotations

from vaultforge.infrastructure.security.password import hash_password, verify_password


def test_hash_and_verify_password() -> None:
    hashed = hash_password("super-secret-password")
    assert hashed != "super-secret-password"
    assert verify_password("super-secret-password", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct-password")
    assert not verify_password("wrong-password", hashed)
