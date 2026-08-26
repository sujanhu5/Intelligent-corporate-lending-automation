"""
Input validation helpers used in Pydantic schemas and service layers.
"""

from __future__ import annotations

import re
from typing import Optional


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_PHONE_RE = re.compile(r"^\+?[0-9\s\-\(\)]{7,20}$")
_REGISTRATION_RE = re.compile(r"^[A-Za-z0-9\-_/]{3,50}$")


def validate_email(value: str) -> str:
    if not _EMAIL_RE.match(value.strip()):
        raise ValueError(f"'{value}' is not a valid email address.")
    return value.strip().lower()


def validate_phone(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    if not _PHONE_RE.match(cleaned):
        raise ValueError(f"'{value}' is not a valid phone number.")
    return cleaned


def validate_loan_amount(value: float) -> float:
    if value <= 0:
        raise ValueError("Loan amount must be greater than zero.")
    if value > 1_000_000_000_000:  # 1 trillion upper sanity cap
        raise ValueError("Loan amount exceeds the maximum allowable limit.")
    return round(value, 2)


def validate_loan_tenure(months: int) -> int:
    if months < 1:
        raise ValueError("Loan tenure must be at least 1 month.")
    if months > 360:  # 30 years max
        raise ValueError("Loan tenure cannot exceed 360 months (30 years).")
    return months


def validate_password_strength(password: str) -> str:
    """
    Enforce a minimum password policy:
    - At least 8 characters
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValueError("Password must contain at least one special character.")
    return password


def sanitise_string(value: str, max_length: int = 1000) -> str:
    """Strip leading/trailing whitespace and truncate to max_length."""
    return value.strip()[:max_length]
