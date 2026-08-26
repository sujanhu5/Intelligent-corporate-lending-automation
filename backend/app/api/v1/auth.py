"""
Authentication endpoints — login, current user, password change, logout.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError
from app.database.connection import get_db
from app.dependencies import get_current_user, get_client_ip
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive a JWT access token",
)
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    service = AuthService(db)
    return service.login(
        request=body,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", "unknown"),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the currently authenticated user's profile",
)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ---------------------------------------------------------------------------
# POST /auth/change-password
# ---------------------------------------------------------------------------

@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change the current user's password",
)
def change_password(
    request: Request,
    body: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = AuthService(db)
    service.change_password(
        user=current_user,
        request=body,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message="Password changed successfully.")


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout (instructs the client to discard the token)",
)
def logout(current_user: User = Depends(get_current_user)) -> MessageResponse:
    # JWT is stateless — actual invalidation requires a token blacklist (Redis).
    # For Phase 1 we rely on short token expiry and client-side deletion.
    return MessageResponse(
        message="Logged out successfully. Please discard your access token."
    )
