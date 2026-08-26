"""ORM model — users table."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, PgEnum

if TYPE_CHECKING:
    from app.models.audit_log import AuditLog
    from app.models.company import Company


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    OFFICER = "officer"
    VIEWER = "viewer"
    COMPANY = "company"


class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        PgEnum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.ANALYST,
    )
    status: Mapped[UserStatus] = mapped_column(
        PgEnum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    profile_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )

    # Relationships
    company: Mapped[Optional["Company"]] = relationship(
        "Company", foreign_keys=[company_id], lazy="joined",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
