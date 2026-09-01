"""Unit tests for OAuth2 infrastructure."""

from __future__ import annotations

import uuid

import pytest

from vaultforge.core.exceptions import AuthenticationError, ValidationError
from vaultforge.infrastructure.security.oauth import (
    GoogleOIDCProvider,
    OAuth2Facade,
    OAuthClient,
    OAuthClientRegistry,
    OAuthClientType,
    OAuthGrantType,
    build_default_client_registry,
    generate_pkce_challenge,
    verify_pkce,
)


def test_pkce_challenge_and_verify() -> None:
    verifier = "test-verifier-string-12345"
    challenge = generate_pkce_challenge(verifier)
    assert verify_pkce(verifier, challenge, "S256")


def test_pkce_invalid_method() -> None:
    with pytest.raises(ValidationError):
        generate_pkce_challenge("verifier", method="plain")


def test_client_registry_unknown_client() -> None:
    registry = OAuthClientRegistry()
    with pytest.raises(AuthenticationError):
        registry.get("missing")


def test_client_secret_validation() -> None:
    client = OAuthClient(
        client_id="app",
        client_secret="secret",
        client_type=OAuthClientType.CONFIDENTIAL,
        allowed_grant_types=frozenset({OAuthGrantType.RESOURCE_OWNER_PASSWORD}),
        redirect_uris=frozenset(),
        scopes=frozenset({"vaultforge.api"}),
    )
    client.validate_secret("secret")
    with pytest.raises(AuthenticationError):
        client.validate_secret("wrong")


def test_build_default_client_registry() -> None:
    registry = build_default_client_registry()
    client = registry.get("vaultforge-web")
    assert OAuthGrantType.RESOURCE_OWNER_PASSWORD in client.allowed_grant_types


def test_oauth_facade_authorization_code() -> None:
    facade = OAuth2Facade.build()
    user_id = uuid.uuid4()
    code = facade.create_authorization_code(
        client_id="vaultforge-web",
        user_id=user_id,
        redirect_uri="http://localhost:3000/oauth/callback",
        scopes=["vaultforge.api"],
    )
    assert len(code) > 20


def test_google_oidc_discovery() -> None:
    provider = GoogleOIDCProvider()
    doc = provider.discovery()
    assert doc.issuer == "https://accounts.google.com"
    assert "openid" in doc.scopes_supported


def test_google_authorization_url() -> None:
    provider = GoogleOIDCProvider()
    url = provider.build_authorization_url(
        client_id="google-client",
        redirect_uri="http://localhost/callback",
        state="xyz",
    )
    assert "accounts.google.com" in url
    assert "client_id=google-client" in url
