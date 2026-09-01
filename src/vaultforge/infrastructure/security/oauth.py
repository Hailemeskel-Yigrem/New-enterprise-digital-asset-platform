"""OAuth2 password grant and optional Google/OIDC provider integrations."""

from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, cast
from urllib.parse import urlencode

import httpx

from vaultforge.core.config import Settings, get_settings
from vaultforge.core.exceptions import AuthenticationError, ValidationError
from vaultforge.infrastructure.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from vaultforge.infrastructure.security.jwt import TOKEN_TYPE_REFRESH


class OAuthGrantType(StrEnum):
    """OAuth 2.0 grant_type identifiers (RFC 6749) — protocol names, not credentials."""

    RESOURCE_OWNER_PASSWORD = "password"
    REFRESH_TOKEN = "refresh_token"
    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"


class OAuthClientType(StrEnum):
    PUBLIC = "public"
    CONFIDENTIAL = "confidential"


@dataclass(slots=True, frozen=True)
class OAuthClient:
    client_id: str
    client_secret: str | None
    client_type: OAuthClientType
    allowed_grant_types: frozenset[OAuthGrantType]
    redirect_uris: frozenset[str]
    scopes: frozenset[str]

    def validate_secret(self, provided: str | None) -> None:
        if self.client_type == OAuthClientType.CONFIDENTIAL and (
            not provided or not secrets.compare_digest(provided, self.client_secret or "")
        ):
            raise AuthenticationError("Invalid client credentials")


@dataclass(slots=True)
class OAuthAuthorizationCode:
    code: str
    client_id: str
    user_id: uuid.UUID
    redirect_uri: str
    scopes: list[str]
    code_challenge: str | None = None
    code_challenge_method: str | None = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(minutes=10))
    consumed: bool = False

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at

    def consume(self) -> None:
        if self.consumed:
            raise AuthenticationError("Authorization code already used")
        if self.is_expired():
            raise AuthenticationError("Authorization code expired")
        self.consumed = True


@dataclass(slots=True)
class OAuthTokenResponse:
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    refresh_token: str | None = None
    scope: str | None = None
    id_token: str | None = None


@dataclass(slots=True)
class OIDCDiscoveryDocument:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str | None = None
    scopes_supported: list[str] = field(default_factory=list)
    response_types_supported: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "jwks_uri": self.jwks_uri,
            "userinfo_endpoint": self.userinfo_endpoint,
            "scopes_supported": self.scopes_supported,
            "response_types_supported": self.response_types_supported,
        }


class InMemoryOAuthCodeStore:
    """Ephemeral authorization-code storage for OAuth/OIDC flows."""

    def __init__(self) -> None:
        self._codes: dict[str, OAuthAuthorizationCode] = {}

    def store(self, auth_code: OAuthAuthorizationCode) -> OAuthAuthorizationCode:
        self._codes[auth_code.code] = auth_code
        return auth_code

    def pop(self, code: str) -> OAuthAuthorizationCode | None:
        return self._codes.pop(code, None)

    def purge_expired(self) -> int:
        expired = [key for key, value in self._codes.items() if value.is_expired()]
        for key in expired:
            del self._codes[key]
        return len(expired)


class OAuthClientRegistry:
    """Registry of registered OAuth clients."""

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClient] = {}

    def register(self, client: OAuthClient) -> None:
        self._clients[client.client_id] = client

    def get(self, client_id: str) -> OAuthClient:
        client = self._clients.get(client_id)
        if client is None:
            raise AuthenticationError("Unknown OAuth client")
        return client


def build_default_client_registry(settings: Settings | None = None) -> OAuthClientRegistry:
    cfg = settings or get_settings()
    registry = OAuthClientRegistry()
    registry.register(
        OAuthClient(
            client_id=cfg.oauth_default_client_id,
            client_secret=cfg.oauth_default_client_secret,
            client_type=OAuthClientType.CONFIDENTIAL,
            allowed_grant_types=frozenset(
                {
                    OAuthGrantType.RESOURCE_OWNER_PASSWORD,
                    OAuthGrantType.REFRESH_TOKEN,
                    OAuthGrantType.AUTHORIZATION_CODE,
                }
            ),
            redirect_uris=frozenset(cfg.oauth_redirect_uris),
            scopes=frozenset({"openid", "profile", "email", "vaultforge.api"}),
        )
    )
    if cfg.oauth_google_client_id:
        registry.register(
            OAuthClient(
                client_id=cfg.oauth_google_client_id,
                client_secret=cfg.oauth_google_client_secret,
                client_type=OAuthClientType.CONFIDENTIAL,
                allowed_grant_types=frozenset({OAuthGrantType.AUTHORIZATION_CODE}),
                redirect_uris=frozenset(cfg.oauth_google_redirect_uris),
                scopes=frozenset({"openid", "profile", "email"}),
            )
        )
    return registry


def generate_authorization_code() -> str:
    return secrets.token_urlsafe(32)


def generate_pkce_challenge(verifier: str, method: str = "S256") -> str:
    if method != "S256":
        raise ValidationError("Only S256 PKCE is supported")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_pkce(verifier: str, challenge: str, method: str | None) -> bool:
    if method is None:
        return True
    expected = generate_pkce_challenge(verifier, method)
    return secrets.compare_digest(expected, challenge)


@dataclass(slots=True)
class PasswordGrantAuthenticator:
    """Authenticate resource-owner password credentials."""

    async def authenticate(
        self,
        email: str,
        password: str,
        *,
        get_user_by_email: Any,
        is_active_check: bool = True,
    ) -> uuid.UUID:
        user = await get_user_by_email(email.lower())
        if user is None:
            raise AuthenticationError("Invalid username or password")
        if not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        if is_active_check and not user.is_active:
            raise AuthenticationError("Account is inactive")
        return cast(uuid.UUID, user.id)


@dataclass(slots=True)
class OAuth2TokenIssuer:
    """Issue OAuth2 access and refresh tokens."""

    settings: Settings | None = None

    def issue_for_user(
        self,
        user_id: uuid.UUID,
        *,
        scopes: list[str] | None = None,
        include_refresh: bool = True,
    ) -> OAuthTokenResponse:
        cfg = self.settings or get_settings()
        access = create_access_token(user_id, settings=cfg)
        refresh = create_refresh_token(user_id, settings=cfg) if include_refresh else None
        return OAuthTokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=cfg.jwt_access_token_expire_minutes * 60,
            scope=" ".join(scopes) if scopes else None,
        )


@dataclass(slots=True)
class OAuth2PasswordGrantHandler:
    client_registry: OAuthClientRegistry
    token_issuer: OAuth2TokenIssuer
    password_authenticator: PasswordGrantAuthenticator

    async def handle(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        username: str,
        password: str,
        scope: str | None,
        get_user_by_email: Any,
    ) -> OAuthTokenResponse:
        client = self.client_registry.get(client_id)
        client.validate_secret(client_secret)
        if OAuthGrantType.RESOURCE_OWNER_PASSWORD not in client.allowed_grant_types:
            raise AuthenticationError("Password grant not allowed for this client")
        scopes = _parse_scopes(scope, client.scopes)
        user_id = await self.password_authenticator.authenticate(
            username,
            password,
            get_user_by_email=get_user_by_email,
        )
        return self.token_issuer.issue_for_user(user_id, scopes=scopes)


@dataclass(slots=True)
class OAuth2RefreshGrantHandler:
    client_registry: OAuthClientRegistry
    token_issuer: OAuth2TokenIssuer

    async def handle(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        refresh_token: str,
        get_user_by_id: Any,
    ) -> OAuthTokenResponse:
        from vaultforge.infrastructure.security import get_user_id_from_token

        client = self.client_registry.get(client_id)
        client.validate_secret(client_secret)
        if OAuthGrantType.REFRESH_TOKEN not in client.allowed_grant_types:
            raise AuthenticationError("Refresh grant not allowed for this client")
        user_id = get_user_id_from_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
        user = await get_user_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account unavailable")
        return self.token_issuer.issue_for_user(user_id)


@dataclass(slots=True)
class OAuth2AuthorizationCodeGrantHandler:
    client_registry: OAuthClientRegistry
    token_issuer: OAuth2TokenIssuer
    code_store: InMemoryOAuthCodeStore

    async def handle(
        self,
        *,
        client_id: str,
        client_secret: str | None,
        code: str,
        redirect_uri: str,
        code_verifier: str | None,
        get_user_by_id: Any,
    ) -> OAuthTokenResponse:
        client = self.client_registry.get(client_id)
        client.validate_secret(client_secret)
        if OAuthGrantType.AUTHORIZATION_CODE not in client.allowed_grant_types:
            raise AuthenticationError("Authorization code grant not allowed")
        if redirect_uri not in client.redirect_uris:
            raise AuthenticationError("Invalid redirect URI")
        auth_code = self.code_store.pop(code)
        if auth_code is None:
            raise AuthenticationError("Invalid authorization code")
        if auth_code.client_id != client_id:
            raise AuthenticationError("Authorization code client mismatch")
        if auth_code.redirect_uri != redirect_uri:
            raise AuthenticationError("Redirect URI mismatch")
        if not verify_pkce(
            code_verifier or "",
            auth_code.code_challenge or "",
            auth_code.code_challenge_method,
        ):
            raise AuthenticationError("PKCE verification failed")
        auth_code.consume()
        user = await get_user_by_id(auth_code.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User account unavailable")
        return self.token_issuer.issue_for_user(auth_code.user_id, scopes=auth_code.scopes)


def _parse_scopes(scope: str | None, allowed: frozenset[str]) -> list[str]:
    if not scope:
        return sorted(allowed)
    requested = [part for part in scope.split() if part]
    invalid = [part for part in requested if part not in allowed]
    if invalid:
        raise ValidationError(f"Invalid scopes: {', '.join(invalid)}")
    return requested


@dataclass(slots=True)
class GoogleOIDCProvider:
    """Google OpenID Connect provider stub with discovery and token exchange."""

    settings: Settings | None = None

    def discovery(self) -> OIDCDiscoveryDocument:
        return OIDCDiscoveryDocument(
            issuer="https://accounts.google.com",
            authorization_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
            token_endpoint="https://oauth2.googleapis.com/token",
            jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
            userinfo_endpoint="https://openidconnect.googleapis.com/v1/userinfo",
            scopes_supported=["openid", "email", "profile"],
            response_types_supported=["code", "token", "id_token", "code token", "code id_token"],
        )

    def build_authorization_url(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: list[str] | None = None,
        nonce: str | None = None,
        code_challenge: str | None = None,
    ) -> str:
        doc = self.discovery()
        params: dict[str, str] = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or ["openid", "email", "profile"]),
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        if nonce:
            params["nonce"] = nonce
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        return f"{doc.authorization_endpoint}?{urlencode(params)}"

    async def exchange_code(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str | None,
        redirect_uri: str,
    ) -> dict[str, Any]:
        doc = self.discovery()
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
        }
        if client_secret:
            payload["client_secret"] = client_secret
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(doc.token_endpoint, data=payload)
        if response.status_code >= 400:
            raise AuthenticationError("Google token exchange failed")
        return cast(dict[str, Any], response.json())

    async def fetch_userinfo(self, access_token: str) -> dict[str, Any]:
        doc = self.discovery()
        endpoint = doc.userinfo_endpoint or ""
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(endpoint, headers=headers)
        if response.status_code >= 400:
            raise AuthenticationError("Failed to fetch Google userinfo")
        return cast(dict[str, Any], response.json())


@dataclass(slots=True)
class GenericOIDCProvider:
    """Generic OIDC provider driven by issuer discovery URL."""

    issuer_url: str
    _discovery: OIDCDiscoveryDocument | None = None

    async def load_discovery(self) -> OIDCDiscoveryDocument:
        if self._discovery is not None:
            return self._discovery
        discovery_url = self.issuer_url.rstrip("/") + "/.well-known/openid-configuration"
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(discovery_url)
        if response.status_code >= 400:
            raise ValidationError("OIDC discovery document unavailable")
        data = response.json()
        self._discovery = OIDCDiscoveryDocument(
            issuer=data["issuer"],
            authorization_endpoint=data["authorization_endpoint"],
            token_endpoint=data["token_endpoint"],
            jwks_uri=data["jwks_uri"],
            userinfo_endpoint=data.get("userinfo_endpoint"),
            scopes_supported=list(data.get("scopes_supported") or []),
            response_types_supported=list(data.get("response_types_supported") or []),
        )
        return self._discovery

    async def build_authorization_url(
        self,
        *,
        client_id: str,
        redirect_uri: str,
        state: str,
        scopes: list[str] | None = None,
    ) -> str:
        doc = await self.load_discovery()
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or doc.scopes_supported or ["openid"]),
            "state": state,
        }
        return f"{doc.authorization_endpoint}?{urlencode(params)}"


@dataclass(slots=True)
class OAuth2Facade:
    """High-level OAuth2 coordinator used by API layer."""

    client_registry: OAuthClientRegistry
    code_store: InMemoryOAuthCodeStore
    password_handler: OAuth2PasswordGrantHandler
    refresh_handler: OAuth2RefreshGrantHandler
    auth_code_handler: OAuth2AuthorizationCodeGrantHandler
    google_provider: GoogleOIDCProvider

    @classmethod
    def build(cls, settings: Settings | None = None) -> OAuth2Facade:
        cfg = settings or get_settings()
        registry = build_default_client_registry(cfg)
        issuer = OAuth2TokenIssuer(settings=cfg)
        codes = InMemoryOAuthCodeStore()
        password = PasswordGrantAuthenticator()
        return cls(
            client_registry=registry,
            code_store=codes,
            password_handler=OAuth2PasswordGrantHandler(registry, issuer, password),
            refresh_handler=OAuth2RefreshGrantHandler(registry, issuer),
            auth_code_handler=OAuth2AuthorizationCodeGrantHandler(registry, issuer, codes),
            google_provider=GoogleOIDCProvider(settings=cfg),
        )

    def create_authorization_code(
        self,
        *,
        client_id: str,
        user_id: uuid.UUID,
        redirect_uri: str,
        scopes: list[str],
        code_challenge: str | None = None,
        code_challenge_method: str | None = None,
    ) -> str:
        client = self.client_registry.get(client_id)
        if redirect_uri not in client.redirect_uris:
            raise ValidationError("Invalid redirect URI")
        code = generate_authorization_code()
        self.code_store.store(
            OAuthAuthorizationCode(
                code=code,
                client_id=client_id,
                user_id=user_id,
                redirect_uri=redirect_uri,
                scopes=scopes,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
            )
        )
        return code


_oauth_facade: OAuth2Facade | None = None


def get_oauth_facade() -> OAuth2Facade:
    global _oauth_facade
    if _oauth_facade is None:
        _oauth_facade = OAuth2Facade.build()
    return _oauth_facade


def reset_oauth_facade() -> None:
    global _oauth_facade
    _oauth_facade = None
