"""
FastAPI dependency functions shared across all route handlers.

Usage::

    @router.get("/protected")
    def protected(current_user: User = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import get_subject_from_token
from app.database.connection import get_db
from app.models.user import User, UserRole, UserStatus


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def _extract_token(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationError(message="Authorization header missing or malformed.")
    return authorization.split(" ", 1)[1]


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

def get_current_user(
    token: str = Depends(_extract_token),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the current authenticated user from the JWT in the Authorization header.
    Raises AuthenticationError if the token is invalid or the user is not active.
    """
    user_id_str = get_subject_from_token(token)
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise AuthenticationError(message="Token subject is not a valid UUID.")

    user: Optional[User] = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError(message="User not found.")
    if user.status != UserStatus.ACTIVE:
        raise AuthenticationError(message="User account is not active.")
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ---------------------------------------------------------------------------
# Role-based access control
# ---------------------------------------------------------------------------

def require_roles(*roles: UserRole):
    """Factory that returns a dependency enforcing one of *roles*."""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise PermissionDeniedError(
                message=f"Requires one of the following roles: {[r.value for r in roles]}."
            )
        return current_user
    return _check


require_admin   = require_roles(UserRole.ADMIN)
require_officer = require_roles(UserRole.ADMIN, UserRole.OFFICER)
require_analyst = require_roles(UserRole.ADMIN, UserRole.OFFICER, UserRole.ANALYST)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 20


def get_pagination(page: int = 1, page_size: int = 20) -> PaginationParams:
    page = max(1, page)
    page_size = max(1, min(100, page_size))  # cap at 100 items per page
    return PaginationParams(page=page, page_size=page_size)


# ---------------------------------------------------------------------------
# Request metadata
# ---------------------------------------------------------------------------

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
