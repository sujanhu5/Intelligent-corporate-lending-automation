"""
Pydantic schemas for loan application endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.models.application import ApplicationStatus, FinalDecision, LoanPurpose
from app.schemas.company import CompanySummary
from app.schemas.user import UserSummary


# =============================================================================
# Request schemas
# =============================================================================

class ApplicationCreate(BaseModel):
    company_id: uuid.UUID
    loan_amount_requested: float
    loan_purpose: LoanPurpose
    loan_tenure_months: int
    interest_rate_requested: Optional[float] = None
    collateral_description: Optional[str] = None
    collateral_value: Optional[float] = None
    officer_notes: Optional[str] = None

    @field_validator("loan_amount_requested")
    @classmethod
    def positive_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Loan amount must be greater than zero.")
        if v > 1_000_000_000_000:
            raise ValueError("Loan amount exceeds the maximum allowed limit.")
        return round(v, 2)

    @field_validator("loan_tenure_months")
    @classmethod
    def valid_tenure(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Loan tenure must be at least 1 month.")
        if v > 360:
            raise ValueError("Loan tenure cannot exceed 360 months (30 years).")
        return v

    @field_validator("interest_rate_requested")
    @classmethod
    def valid_rate(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Interest rate must be between 0 and 100.")
        return v

    @field_validator("collateral_value")
    @classmethod
    def valid_collateral(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Collateral value cannot be negative.")
        return v

    model_config = {"str_strip_whitespace": True}


class ApplicationUpdate(BaseModel):
    loan_amount_requested: Optional[float] = None
    loan_purpose: Optional[LoanPurpose] = None
    loan_tenure_months: Optional[int] = None
    interest_rate_requested: Optional[float] = None
    collateral_description: Optional[str] = None
    collateral_value: Optional[float] = None
    officer_notes: Optional[str] = None
    assigned_officer_id: Optional[uuid.UUID] = None

    model_config = {"str_strip_whitespace": True}


class ApplicationDecisionUpdate(BaseModel):
    decision: FinalDecision
    decision_reason: str
    officer_notes: Optional[str] = None

    @field_validator("decision_reason")
    @classmethod
    def non_empty_reason(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Decision reason cannot be empty.")
        return v.strip()

    @field_validator("decision")
    @classmethod
    def not_pending(cls, v: FinalDecision) -> FinalDecision:
        if v == FinalDecision.PENDING:
            raise ValueError("Cannot set decision to 'pending'.")
        return v


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    reason: Optional[str] = None


# =============================================================================
# Response schemas
# =============================================================================

class PipelineStatus(BaseModel):
    """Shows which pipeline stages have completed for this application."""
    ocr_completed: bool
    ratios_calculated: bool
    rules_evaluated: bool
    ml_predicted: bool
    report_generated: bool


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    application_number: str
    company_id: uuid.UUID
    company: Optional[CompanySummary] = None
    assigned_officer_id: Optional[uuid.UUID]
    assigned_officer: Optional[UserSummary] = None
    loan_amount_requested: float
    loan_purpose: LoanPurpose
    loan_tenure_months: int
    interest_rate_requested: Optional[float]
    collateral_description: Optional[str]
    collateral_value: Optional[float]
    status: ApplicationStatus
    pipeline: PipelineStatus
    final_decision: FinalDecision
    decision_reason: Optional[str]
    officer_notes: Optional[str]
    risk_score: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_relations(cls, app) -> "ApplicationResponse":
        """Build response including nested company + officer summaries."""
        pipeline = PipelineStatus(
            ocr_completed=app.ocr_completed,
            ratios_calculated=app.ratios_calculated,
            rules_evaluated=app.rules_evaluated,
            ml_predicted=app.ml_predicted,
            report_generated=app.report_generated,
        )
        return cls(
            id=app.id,
            application_number=app.application_number,
            company_id=app.company_id,
            company=CompanySummary.model_validate(app.company) if app.company else None,
            assigned_officer_id=app.assigned_officer_id,
            assigned_officer=None,  # loaded separately when needed
            loan_amount_requested=float(app.loan_amount_requested),
            loan_purpose=app.loan_purpose,
            loan_tenure_months=app.loan_tenure_months,
            interest_rate_requested=float(app.interest_rate_requested) if app.interest_rate_requested else None,
            collateral_description=app.collateral_description,
            collateral_value=float(app.collateral_value) if app.collateral_value else None,
            status=app.status,
            pipeline=pipeline,
            final_decision=app.final_decision,
            decision_reason=app.decision_reason,
            officer_notes=app.officer_notes,
            risk_score=float(app.risk_score) if app.risk_score else None,
            created_at=app.created_at,
            updated_at=app.updated_at,
        )


class ApplicationListResponse(BaseModel):
    items: List[ApplicationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApplicationSummary(BaseModel):
    """Lightweight application reference used in company detail responses."""
    id: uuid.UUID
    application_number: str
    status: ApplicationStatus
    final_decision: FinalDecision
    loan_amount_requested: float
    risk_score: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}
