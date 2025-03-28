"""Authentication API routes."""

from __future__ import annotations

from fastapi import APIRouter

from vaultforge.api.deps import AuthServiceDep, CurrentUser, _raise_http
from vaultforge.application.identity.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from vaultforge.core.exceptions import VaultForgeError

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(payload: RegisterRequest, auth_service: AuthServiceDep) -> UserResponse:
    try:
        return await auth_service.register(payload)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> TokenResponse:
    try:
        return await auth_service.login(payload)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, auth_service: AuthServiceDep) -> TokenResponse:
    try:
        return await auth_service.refresh(payload)
    except VaultForgeError as exc:
        _raise_http(exc)
        raise AssertionError("unreachable")


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return current_user
