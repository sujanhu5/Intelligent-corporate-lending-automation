"""ORM model — companies table."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, PgEnum

if TYPE_CHECKING:
    from app.models.application import Application


class CompanyType(str, enum.Enum):
    PRIVATE_LIMITED = "private_limited"
    PUBLIC_LIMITED = "public_limited"
    PARTNERSHIP = "partnership"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    LLP = "llp"
    OTHER = "other"


class CompanyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_REVIEW = "under_review"
    BLACKLISTED = "blacklisted"


class Industry(str, enum.Enum):
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    WHOLESALE = "wholesale"
    SERVICES = "services"
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    CONSTRUCTION = "construction"
    REAL_ESTATE = "real_estate"
    AGRICULTURE = "agriculture"
    FINANCIAL = "financial"
    HOSPITALITY = "hospitality"
    TRANSPORTATION = "transportation"
    ENERGY = "energy"
    OTHER = "other"


class Company(Base):
    __tablename__ = "companies"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registration_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    tax_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    gst_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Classification
    company_type: Mapped[CompanyType] = mapped_column(
        PgEnum(CompanyType, name="company_type"), nullable=False
    )
    industry: Mapped[Industry] = mapped_column(
        PgEnum(Industry, name="industry"), nullable=False
    )
    status: Mapped[CompanyStatus] = mapped_column(
        PgEnum(CompanyStatus, name="company_status"),
        nullable=False,
        default=CompanyStatus.ACTIVE,
    )

    # Incorporation
    incorporation_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country_of_incorporation: Mapped[str] = mapped_column(String(100), default="India")

    # Contact
    registered_address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Financial profile (high-level; detailed data lives in application docs)
    annual_turnover: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)
    number_of_employees: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    applications: Mapped[List["Application"]] = relationship(
        "Application", back_populates="company", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"
