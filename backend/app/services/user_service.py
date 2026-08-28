"""
UserService — user management business logic (CRUD, status changes).
Enforces business rules that belong in the domain, not in the route handler.
"""

from __future__ import annotations

import math
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole, UserStatus
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserAdminUpdate,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserStatusUpdate,
    UserUpdate,
)

logger = get_logger(__name__)


class UserService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._user_repo = UserRepository(db)
        self._audit_repo = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, user_id: uuid.UUID) -> User:
        user = self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError(message=f"User '{user_id}' not found.")
        return user

    def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None,
    ) -> UserListResponse:
        users, total = self._user_repo.list(
            page=page,
            page_size=page_size,
            role=role,
            status=status,
            search=search,
        )
        total_pages = max(1, math.ceil(total / page_size))
        return UserListResponse(
            items=[UserResponse.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def create_user(
        self,
        data: UserCreate,
        created_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> User:
        if self._user_repo.exists_by_email(data.email):
            raise ConflictError(
                message=f"An account with email '{data.email}' already exists."
            )

        user = self._user_repo.create(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=data.role,
            department=data.department,
            phone=data.phone,
            profile_notes=data.profile_notes,
            is_verified=True,
        )

        self._audit_repo.log(
            action=AuditAction.USER_CREATED,
            description=f"User '{user.email}' created by '{created_by.email}'.",
            user_id=created_by.id,
            entity_type="user",
            entity_id=str(user.id),
            new_values={"email": user.email, "role": user.role.value},
            ip_address=ip_address,
            request_id=request_id,
        )
        return user

    # -------------------------------------------------------------------------
    # Update (self-update — limited fields)
    # -------------------------------------------------------------------------

    def update_own_profile(
        self,
        user: User,
        data: UserUpdate,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> User:
        old = {
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "department": user.department,
        }
        updates = data.model_dump(exclude_none=True)

        # Uniqueness check when changing email
        if "email" in updates and updates["email"].lower() != user.email.lower():
            new_email = updates["email"].lower()
            existing = self._user_repo.get_by_email(new_email)
            if existing and existing.id != user.id:
                raise ConflictError(message=f"Email '{new_email}' is already in use.")
            updates["email"] = new_email

        self._user_repo.update(user, **updates)

        self._audit_repo.log(
            action=AuditAction.USER_UPDATED,
            description=f"User '{user.email}' updated their own profile.",
            user_id=user.id,
            entity_type="user",
            entity_id=str(user.id),
            old_values=old,
            new_values=updates,
            ip_address=ip_address,
            request_id=request_id,
        )
        return user

    # -------------------------------------------------------------------------
    # Admin update (full fields including role, status)
    # -------------------------------------------------------------------------

    def admin_update_user(
        self,
        target_id: uuid.UUID,
        data: UserAdminUpdate,
        admin: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> User:
        target = self.get_by_id(target_id)

        # Prevent an admin from stripping their own admin role
        if str(target.id) == str(admin.id) and data.role and data.role != UserRole.ADMIN:
            raise PermissionDeniedError(
                message="You cannot remove your own admin role."
            )

        old = {
            "role": target.role.value,
            "status": target.status.value,
            "full_name": target.full_name,
        }
        updates = data.model_dump(exclude_none=True)
        self._user_repo.update(target, **updates)

        self._audit_repo.log(
            action=AuditAction.USER_UPDATED,
            description=f"Admin '{admin.email}' updated user '{target.email}'.",
            user_id=admin.id,
            entity_type="user",
            entity_id=str(target.id),
            old_values=old,
            new_values=updates,
            ip_address=ip_address,
            request_id=request_id,
        )
        return target

    # -------------------------------------------------------------------------
    # Status change
    # -------------------------------------------------------------------------

    def update_user_status(
        self,
        target_id: uuid.UUID,
        data: UserStatusUpdate,
        admin: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> User:
        target = self.get_by_id(target_id)

        if str(target.id) == str(admin.id):
            raise PermissionDeniedError(
                message="You cannot change your own account status."
            )

        old_status = target.status
        self._user_repo.set_status(target, data.status)

        self._audit_repo.log(
            action=AuditAction.USER_UPDATED,
            description=(
                f"Status of user '{target.email}' changed from "
                f"'{old_status.value}' to '{data.status.value}' "
                f"by '{admin.email}'. Reason: {data.reason or 'N/A'}"
            ),
            user_id=admin.id,
            entity_type="user",
            entity_id=str(target.id),
            old_values={"status": old_status.value},
            new_values={"status": data.status.value, "reason": data.reason},
            ip_address=ip_address,
            request_id=request_id,
        )
        return target

    # -------------------------------------------------------------------------
    # Deactivate (soft delete)
    # -------------------------------------------------------------------------

    def deactivate_user(
        self,
        target_id: uuid.UUID,
        admin: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> User:
        target = self.get_by_id(target_id)

        if str(target.id) == str(admin.id):
            raise PermissionDeniedError(
                message="You cannot deactivate your own account."
            )

        self._user_repo.soft_delete(target)

        self._audit_repo.log(
            action=AuditAction.USER_UPDATED,
            description=f"User '{target.email}' deactivated by '{admin.email}'.",
            user_id=admin.id,
            entity_type="user",
            entity_id=str(target.id),
            old_values={"status": "active"},
            new_values={"status": "inactive"},
            ip_address=ip_address,
            request_id=request_id,
        )
        return target
