"""
JWT token creation/verification and bcrypt password hashing utilities.
Never import the raw jose/passlib libraries outside this module.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import AuthenticationError

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

_TOKEN_TYPE = "bearer"


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT.

    Args:
        subject:      Unique identifier (usually user UUID as string).
        extra_claims: Additional claims to embed (e.g. role, email).
        expires_delta: Override the default expiry configured in settings.
    """
    now = datetime.now(tz=timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT, returning its claims.

    Raises:
        AuthenticationError: if the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise AuthenticationError(message=str(exc)) from exc

    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type.")

    return payload


def get_subject_from_token(token: str) -> str:
    """Return the 'sub' claim from a valid token."""
    payload = decode_access_token(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError(message="Token missing subject claim.")
    return str(sub)
