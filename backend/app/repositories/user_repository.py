"""
UserRepository — all database operations for the users table.
Service layer calls this; route handlers never touch the ORM directly.
"""

from __future__ import annotations

import math
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.user import User, UserRole, UserStatus


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self._db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return (
            self._db.query(User)
            .filter(func.lower(User.email) == email.lower().strip())
            .first()
        )

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        """
        Returns (users_on_page, total_count).
        Supports filtering by role/status and fuzzy name/email search.
        """
        q = self._db.query(User)

        if role:
            q = q.filter(User.role == role)
        if status:
            q = q.filter(User.status == status)
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    User.email.ilike(like),
                    User.full_name.ilike(like),
                    User.department.ilike(like),
                )
            )

        total = q.count()
        offset = (page - 1) * page_size
        users = (
            q.order_by(User.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return users, total

    def exists_by_email(self, email: str) -> bool:
        return (
            self._db.query(User.id)
            .filter(func.lower(User.email) == email.lower().strip())
            .first()
        ) is not None

    # -------------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------------

    def create(
        self,
        email: str,
        full_name: str,
        hashed_password: str,
        role: UserRole = UserRole.ANALYST,
        department: Optional[str] = None,
        phone: Optional[str] = None,
        profile_notes: Optional[str] = None,
        is_verified: bool = False,
    ) -> User:
        user = User(
            email=email.lower().strip(),
            full_name=full_name.strip(),
            hashed_password=hashed_password,
            role=role,
            status=UserStatus.ACTIVE,
            department=department,
            phone=phone,
            profile_notes=profile_notes,
            is_verified=is_verified,
        )
        self._db.add(user)
        self._db.flush()  # get the generated id without committing
        return user

    def update(self, user: User, **fields) -> User:
        """Apply arbitrary field updates to a User instance."""
        for key, value in fields.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        self._db.flush()
        return user

    def update_last_login(self, user: User, timestamp: str) -> None:
        user.last_login = timestamp
        self._db.flush()

    def update_password(self, user: User, new_hashed_password: str) -> None:
        user.hashed_password = new_hashed_password
        self._db.flush()

    def set_status(self, user: User, status: UserStatus) -> User:
        user.status = status
        self._db.flush()
        return user

    def soft_delete(self, user: User) -> User:
        """Deactivate a user — hard deletion is not supported."""
        user.status = UserStatus.INACTIVE
        self._db.flush()
        return user
