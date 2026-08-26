"""
Pydantic schemas for company endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from app.models.company import CompanyStatus, CompanyType, Industry


# =============================================================================
# Request schemas
# =============================================================================

class CompanyCreate(BaseModel):
    name: str
    registration_number: str
    tax_id: Optional[str] = None
    gst_number: Optional[str] = None
    company_type: CompanyType
    industry: Industry
    incorporation_date: Optional[str] = None       # ISO date string "YYYY-MM-DD"
    country_of_incorporation: str = "India"
    registered_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    annual_turnover: Optional[float] = None
    number_of_employees: Optional[int] = None
    notes: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Company name must be at least 2 characters.")
        return v

    @field_validator("registration_number")
    @classmethod
    def validate_reg_number(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Registration number must be at least 3 characters.")
        return v.upper()

    @field_validator("annual_turnover")
    @classmethod
    def validate_turnover(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Annual turnover cannot be negative.")
        return v

    @field_validator("number_of_employees")
    @classmethod
    def validate_employees(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("Number of employees cannot be negative.")
        return v

    model_config = {"str_strip_whitespace": True}


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    tax_id: Optional[str] = None
    gst_number: Optional[str] = None
    company_type: Optional[CompanyType] = None
    industry: Optional[Industry] = None
    incorporation_date: Optional[str] = None
    country_of_incorporation: Optional[str] = None
    registered_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    annual_turnover: Optional[float] = None
    number_of_employees: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[CompanyStatus] = None

    model_config = {"str_strip_whitespace": True}


# =============================================================================
# Response schemas
# =============================================================================

class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    registration_number: str
    tax_id: Optional[str]
    gst_number: Optional[str]
    company_type: CompanyType
    industry: Industry
    status: CompanyStatus
    incorporation_date: Optional[str]
    country_of_incorporation: str
    registered_address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    website: Optional[str]
    annual_turnover: Optional[float]
    number_of_employees: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Computed: how many applications this company has submitted
    application_count: Optional[int] = None

    model_config = {"from_attributes": True}


class CompanyListResponse(BaseModel):
    items: List[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CompanySummary(BaseModel):
    """Lightweight company reference embedded in application responses."""
    id: uuid.UUID
    name: str
    registration_number: str
    industry: Industry
    company_type: CompanyType
    status: CompanyStatus

    model_config = {"from_attributes": True}
