"""
User management endpoints — CRUD for admin, profile update for self.
"""

from __future__ import annotations

import uuid
from pydantic import BaseModel

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import (
    PaginationParams,
    get_client_ip,
    get_current_user,
    get_pagination,
    require_admin,
)
from app.models.user import User, UserRole, UserStatus
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    UserAdminUpdate,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /users  (admin only)
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all users (admin only)",
)
def list_users(
    request: Request,
    role: UserRole | None = Query(default=None, description="Filter by role"),
    user_status: UserStatus | None = Query(
        default=None, alias="status", description="Filter by status"
    ),
    search: str | None = Query(default=None, description="Search name or email"),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserListResponse:
    service = UserService(db)
    return service.list_users(
        page=pagination.page,
        page_size=pagination.page_size,
        role=role,
        status=user_status,
        search=search,
    )


# ---------------------------------------------------------------------------
# POST /users  (admin only)
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin only)",
)
def create_user(
    request: Request,
    body: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    service = UserService(db)
    return service.create_user(
        data=body,
        created_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# GET /users/{user_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a user by ID",
)
def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    service = UserService(db)
    return service.get_by_id(user_id)


# ---------------------------------------------------------------------------
# PUT /users/{user_id}  (admin update — full fields)
# ---------------------------------------------------------------------------

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a user (admin only)",
)
def admin_update_user(
    request: Request,
    user_id: uuid.UUID,
    body: UserAdminUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    service = UserService(db)
    return service.admin_update_user(
        target_id=user_id,
        data=body,
        admin=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# PATCH /users/me  (self-update — limited fields)
# ---------------------------------------------------------------------------

@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update your own profile",
)
def update_own_profile(
    request: Request,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    service = UserService(db)
    return service.update_own_profile(
        user=current_user,
        data=body,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# PATCH /users/{user_id}/status  (admin only)
# ---------------------------------------------------------------------------

@router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Change a user's account status (admin only)",
)
def update_user_status(
    request: Request,
    user_id: uuid.UUID,
    body: UserStatusUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    service = UserService(db)
    return service.update_user_status(
        target_id=user_id,
        data=body,
        admin=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}  (admin only — soft delete)
# ---------------------------------------------------------------------------

@router.delete(
    "/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a user account (admin only)",
)
def deactivate_user(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = UserService(db)
    service.deactivate_user(
        target_id=user_id,
        admin=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message=f"User '{user_id}' has been deactivated.")


# ---------------------------------------------------------------------------
# POST /users/{user_id}/reset-password  (admin only)
# ---------------------------------------------------------------------------

class PasswordResetBody(BaseModel):
    new_password: str


@router.post(
    "/{user_id}/reset-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset a user's password (admin only)",
)
def reset_user_password(
    request: Request,
    user_id: uuid.UUID,
    body: PasswordResetBody,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    from app.utils.validators import validate_password_strength
    validate_password_strength(body.new_password)

    user_service = UserService(db)
    target = user_service.get_by_id(user_id)

    auth_service = AuthService(db)
    auth_service.admin_reset_password(
        target_user=target,
        new_password=body.new_password,
        admin=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message=f"Password for user '{target.email}' has been reset.")

