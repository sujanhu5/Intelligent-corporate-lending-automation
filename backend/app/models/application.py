"""ORM model — loan_applications table."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, PgEnum

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.document import Document
    from app.models.financial_ratio import FinancialRatio
    from app.models.prediction import Prediction
    from app.models.report import Report


class ApplicationStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    OCR_PROCESSING = "ocr_processing"
    OCR_COMPLETE = "ocr_complete"
    RATIO_CALCULATED = "ratio_calculated"
    RULE_EVALUATED = "rule_evaluated"
    ML_PREDICTED = "ml_predicted"
    REPORT_GENERATED = "report_generated"
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    WITHDRAWN = "withdrawn"


class LoanPurpose(str, enum.Enum):
    WORKING_CAPITAL = "working_capital"
    CAPITAL_EXPENDITURE = "capital_expenditure"
    DEBT_REFINANCING = "debt_refinancing"
    EXPANSION = "expansion"
    ACQUISITION = "acquisition"
    TRADE_FINANCE = "trade_finance"
    OTHER = "other"


class FinalDecision(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    MANUAL_REVIEW = "manual_review"
    PENDING = "pending"


class Application(Base):
    __tablename__ = "loan_applications"

    # Application reference
    application_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )

    # Foreign keys
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    assigned_officer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Loan details
    loan_amount_requested: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    loan_purpose: Mapped[LoanPurpose] = mapped_column(
        PgEnum(LoanPurpose, name="loan_purpose"), nullable=False
    )
    loan_tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    interest_rate_requested: Mapped[Optional[float]] = mapped_column(Numeric(6, 4), nullable=True)
    collateral_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    collateral_value: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)

    # Processing status
    status: Mapped[ApplicationStatus] = mapped_column(
        PgEnum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.DRAFT,
    )

    # Pipeline stage flags
    ocr_completed: Mapped[bool] = mapped_column(default=False)
    ratios_calculated: Mapped[bool] = mapped_column(default=False)
    rules_evaluated: Mapped[bool] = mapped_column(default=False)
    ml_predicted: Mapped[bool] = mapped_column(default=False)
    report_generated: Mapped[bool] = mapped_column(default=False)

    # Final decision
    final_decision: Mapped[FinalDecision] = mapped_column(
        PgEnum(FinalDecision, name="final_decision"),
        nullable=False,
        default=FinalDecision.PENDING,
    )
    decision_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    officer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Risk score (0–100)
    risk_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)

    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="applications")
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="application", lazy="dynamic"
    )
    financial_ratios: Mapped[List["FinancialRatio"]] = relationship(
        "FinancialRatio", back_populates="application", lazy="dynamic"
    )
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", back_populates="application", lazy="dynamic"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="application", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} number={self.application_number} "
            f"status={self.status}>"
        )
