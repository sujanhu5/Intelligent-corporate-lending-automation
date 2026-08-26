"""
Pydantic schemas for user management endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.user import UserRole, UserStatus
from app.utils.validators import validate_password_strength, validate_phone


# =============================================================================
# Request schemas
# =============================================================================

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.ANALYST
    department: Optional[str] = None
    phone: Optional[str] = None
    profile_notes: Optional[str] = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("full_name")
    @classmethod
    def non_empty_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Full name cannot be empty.")
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone(v)

    model_config = {"str_strip_whitespace": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    profile_notes: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def non_empty_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if len(v) < 2:
                raise ValueError("Full name must be at least 2 characters.")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_phone(v)

    model_config = {"str_strip_whitespace": True}


class UserAdminUpdate(UserUpdate):
    """Extended update schema — admin-only fields."""
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserStatusUpdate(BaseModel):
    status: UserStatus
    reason: Optional[str] = None


# =============================================================================
# Response schemas
# =============================================================================

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    department: Optional[str]
    phone: Optional[str]
    is_verified: bool
    last_login: Optional[str]
    profile_notes: Optional[str]
    company_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserSummary(BaseModel):
    """Lightweight user reference used inside other response bodies."""
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole

    model_config = {"from_attributes": True}
