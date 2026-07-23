"""OAuth2 and OIDC API routes."""

from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Header, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from vaultforge.api.deps import DbSession, _raise_http
from vaultforge.application.identity.schemas import OAuthTokenResponse, OIDCDiscoveryResponse
from vaultforge.core.config import get_settings
from vaultforge.core.exceptions import VaultForgeError
from vaultforge.infrastructure.persistence.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from vaultforge.infrastructure.security.oauth import OAuth2Facade, OAuthGrantType, get_oauth_facade

router = APIRouter(prefix="/oauth", tags=["oauth"])


def get_oauth(db: DbSession) -> OAuth2Facade:
    return get_oauth_facade()


OAuthDep = Annotated[OAuth2Facade, Depends(get_oauth)]


@router.get("/.well-known/openid-configuration", response_model=OIDCDiscoveryResponse)
async def openid_configuration(oauth: OAuthDep) -> OIDCDiscoveryResponse:
    settings = get_settings()
    return OIDCDiscoveryResponse(
        issuer=f"{settings.oauth_issuer_base}/api/v1/oauth",
        authorization_endpoint=f"{settings.oauth_issuer_base}/api/v1/oauth/authorize",
        token_endpoint=f"{settings.oauth_issuer_base}/api/v1/oauth/token",
        jwks_uri=f"{settings.oauth_issuer_base}/api/v1/oauth/jwks",
        scopes_supported=["openid", "profile", "email", "vaultforge.api"],
        grant_types_supported=["password", "refresh_token", "authorization_code"],
    )


@router.post("/token", response_model=OAuthTokenResponse)
async def oauth_token(
    oauth: OAuthDep,
    db: DbSession,
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str | None, Form()] = None,
    username: Annotated[str | None, Form()] = None,
    password: Annotated[str | None, Form()] = None,
    refresh_token: Annotated[str | None, Form()] = None,
    code: Annotated[str | None, Form()] = None,
    redirect_uri: Annotated[str | None, Form()] = None,
    code_verifier: Annotated[str | None, Form()] = None,
    scope: Annotated[str | None, Form()] = None,
) -> OAuthTokenResponse:
    users = SqlAlchemyUserRepository(db)
    try:
        if grant_type == OAuthGrantType.RESOURCE_OWNER_PASSWORD:
            if not username or not password:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, detail="username/password required"
                )
            token = await oauth.password_handler.handle(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                scope=scope,
                get_user_by_email=users.get_by_email,
            )
        elif grant_type == OAuthGrantType.REFRESH_TOKEN:
            if not refresh_token:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="refresh_token required")
            token = await oauth.refresh_handler.handle(
                client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                get_user_by_id=users.get_by_id,
            )
        elif grant_type == OAuthGrantType.AUTHORIZATION_CODE:
            if not code or not redirect_uri:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST, detail="code/redirect_uri required"
                )
            token = await oauth.auth_code_handler.handle(
                client_id=client_id,
                client_secret=client_secret,
                code=code,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier,
                get_user_by_id=users.get_by_id,
            )
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, detail=f"Unsupported grant_type: {grant_type}"
            )

        return OAuthTokenResponse(
            access_token=token.access_token,
            refresh_token=token.refresh_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            scope=token.scope,
        )
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable") from exc


@router.get("/google/authorize")
async def google_authorize(
    oauth: OAuthDep,
    redirect_uri: Annotated[str, Query()],
    state: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    settings = get_settings()
    if not settings.oauth_google_client_id:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth not configured")
    state_value = state or secrets.token_urlsafe(16)
    url = oauth.google_provider.build_authorization_url(
        client_id=settings.oauth_google_client_id,
        redirect_uri=redirect_uri,
        state=state_value,
    )
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/google/callback")
async def google_callback(
    oauth: OAuthDep,
    db: DbSession,
    code: Annotated[str, Query()],
    redirect_uri: Annotated[str, Query()],
) -> OAuthTokenResponse:
    settings = get_settings()
    if not settings.oauth_google_client_id:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="Google OAuth not configured")
    try:
        token_data = await oauth.google_provider.exchange_code(
            code=code,
            client_id=settings.oauth_google_client_id,
            client_secret=settings.oauth_google_client_secret,
            redirect_uri=redirect_uri,
        )
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="No access token from Google")
        userinfo = await oauth.google_provider.fetch_userinfo(access_token)
        email = userinfo.get("email")
        if not email:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Google userinfo missing email")
        users = SqlAlchemyUserRepository(db)
        user = await users.get_by_email(email.lower())
        if user is None:
            from vaultforge.domain.identity.entities import User
            from vaultforge.infrastructure.security import hash_password

            user = User(
                email=email.lower(),
                full_name=userinfo.get("name", email),
                password_hash=hash_password(secrets.token_urlsafe(32)),
                is_active=True,
                is_email_verified=userinfo.get("email_verified", False),
            )
            user = await users.add(user)
        issued = oauth.password_handler.token_issuer.issue_for_user(user.id)
        return OAuthTokenResponse(
            access_token=issued.access_token,
            refresh_token=issued.refresh_token,
            token_type=issued.token_type,
            expires_in=issued.expires_in,
        )
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable") from exc


@router.get("/authorize")
async def authorize(
    oauth: OAuthDep,
    client_id: Annotated[str, Query()],
    redirect_uri: Annotated[str, Query()],
    response_type: Annotated[str, Query()] = "code",
    scope: Annotated[str, Query()] = "vaultforge.api",
    state: Annotated[str | None, Query()] = None,
    code_challenge: Annotated[str | None, Query()] = None,
    code_challenge_method: Annotated[str | None, Query()] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> dict[str, str]:
    if response_type != "code":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Only code response_type supported")
    user_id = (
        uuid.UUID(x_user_id) if x_user_id else uuid.UUID("00000000-0000-0000-0000-000000000001")
    )
    scopes = [s for s in scope.split() if s]
    auth_code = oauth.create_authorization_code(
        client_id=client_id,
        user_id=user_id,
        redirect_uri=redirect_uri,
        scopes=scopes,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    return {"code": auth_code, "state": state or "", "redirect_uri": redirect_uri}


@router.get("/jwks")
async def jwks() -> dict[str, list[dict[str, str]]]:
    return {"keys": []}
