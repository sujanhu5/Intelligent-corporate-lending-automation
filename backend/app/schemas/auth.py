"""
Pydantic schemas for authentication endpoints.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.utils.validators import validate_password_strength


# =============================================================================
# Request schemas
# =============================================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = {"str_strip_whitespace": True}


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:  # type: ignore[override]
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Passwords do not match.")
        return v

    model_config = {"str_strip_whitespace": True}


class PasswordResetRequest(BaseModel):
    email: EmailStr


# =============================================================================
# Response schemas
# =============================================================================

class TokenUserPayload(BaseModel):
    """Minimal user info embedded in the token response."""
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds until expiry
    user: TokenUserPayload


class MessageResponse(BaseModel):
    message: str
    success: bool = True
