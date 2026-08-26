"""
ApplicationRepository — all database operations for the loan_applications table.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.application import (
    Application,
    ApplicationStatus,
    FinalDecision,
    LoanPurpose,
)
from app.models.company import Company


_TERMINAL_STATUSES = frozenset({
    ApplicationStatus.APPROVED,
    ApplicationStatus.REJECTED,
    ApplicationStatus.MANUAL_REVIEW,
    ApplicationStatus.WITHDRAWN,
})


class ApplicationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, app_id: uuid.UUID, load_company: bool = True) -> Optional[Application]:
        q = self._db.query(Application).filter(Application.id == app_id)
        if load_company:
            q = q.options(joinedload(Application.company))
        return q.first()

    def get_by_application_number(self, number: str) -> Optional[Application]:
        return (
            self._db.query(Application)
            .options(joinedload(Application.company))
            .filter(Application.application_number == number.strip().upper())
            .first()
        )

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        company_id: Optional[uuid.UUID] = None,
        status: Optional[ApplicationStatus] = None,
        final_decision: Optional[FinalDecision] = None,
        assigned_officer_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Application], int]:
        q = (
            self._db.query(Application)
            .options(joinedload(Application.company))
        )

        if company_id:
            q = q.filter(Application.company_id == company_id)
        if status:
            q = q.filter(Application.status == status)
        if final_decision:
            q = q.filter(Application.final_decision == final_decision)
        if assigned_officer_id:
            q = q.filter(Application.assigned_officer_id == assigned_officer_id)
        if search:
            like = f"%{search.strip()}%"
            # Join Company to search by company name
            q = q.join(Company, Application.company_id == Company.id)
            q = q.filter(
                or_(
                    Application.application_number.ilike(like),
                    Company.name.ilike(like),
                    Company.registration_number.ilike(like),
                )
            )

        total = q.count()
        offset = (page - 1) * page_size
        apps = (
            q.order_by(Application.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return apps, total

    def get_by_company(self, company_id: uuid.UUID) -> List[Application]:
        return (
            self._db.query(Application)
            .filter(Application.company_id == company_id)
            .order_by(Application.created_at.desc())
            .all()
        )

    def get_next_sequence_number(self, date_prefix: str) -> int:
        """
        Count applications created today to generate a sequential number.
        date_prefix format: "YYYYMMDD"
        """
        like_pattern = f"CLA-{date_prefix}-%"
        count = (
            self._db.query(func.count(Application.id))
            .filter(Application.application_number.like(like_pattern))
            .scalar()
            or 0
        )
        return count + 1

    def dashboard_stats(self) -> Dict:
        """Aggregate counts for dashboard KPIs."""
        total = self._db.query(func.count(Application.id)).scalar() or 0
        approved = (
            self._db.query(func.count(Application.id))
            .filter(Application.final_decision == FinalDecision.APPROVED)
            .scalar() or 0
        )
        rejected = (
            self._db.query(func.count(Application.id))
            .filter(Application.final_decision == FinalDecision.REJECTED)
            .scalar() or 0
        )
        manual = (
            self._db.query(func.count(Application.id))
            .filter(Application.final_decision == FinalDecision.MANUAL_REVIEW)
            .scalar() or 0
        )
        pending = (
            self._db.query(func.count(Application.id))
            .filter(Application.final_decision == FinalDecision.PENDING)
            .scalar() or 0
        )
        avg_risk = (
            self._db.query(func.avg(Application.risk_score))
            .filter(Application.risk_score.isnot(None))
            .scalar()
        )
        total_disbursed = (
            self._db.query(func.sum(Application.loan_amount_requested))
            .filter(Application.final_decision == FinalDecision.APPROVED)
            .scalar()
        )
        status_counts = dict(
            self._db.query(Application.status, func.count(Application.id))
            .group_by(Application.status)
            .all()
        )
        # Everything between submission and a final decision.
        in_pipeline = sum(
            status_counts.get(s, 0)
            for s in (
                ApplicationStatus.UNDER_REVIEW,
                ApplicationStatus.OCR_PROCESSING,
                ApplicationStatus.OCR_COMPLETE,
                ApplicationStatus.RATIO_CALCULATED,
                ApplicationStatus.RULE_EVALUATED,
                ApplicationStatus.ML_PREDICTED,
                ApplicationStatus.REPORT_GENERATED,
            )
        )

        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "manual_review": manual,
            "pending": pending,
            "draft": status_counts.get(ApplicationStatus.DRAFT, 0),
            "submitted": status_counts.get(ApplicationStatus.SUBMITTED, 0),
            "in_pipeline": in_pipeline,
            "withdrawn": status_counts.get(ApplicationStatus.WITHDRAWN, 0),
            "approval_rate": round((approved / total * 100), 1) if total else 0,
            "avg_risk_score": round(float(avg_risk), 2) if avg_risk else 0,
            "total_loan_amount_approved": float(total_disbursed) if total_disbursed else 0,
        }

    # -------------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------------

    def create(self, **kwargs) -> Application:
        app = Application(**kwargs)
        self._db.add(app)
        self._db.flush()
        return app

    def update(self, app: Application, **fields) -> Application:
        for key, value in fields.items():
            if hasattr(app, key):
                setattr(app, key, value)
        self._db.flush()
        return app

    def update_status(self, app: Application, status: ApplicationStatus) -> Application:
        app.status = status
        self._db.flush()
        return app

    def update_decision(
        self,
        app: Application,
        decision: FinalDecision,
        reason: str,
        officer_notes: Optional[str] = None,
    ) -> Application:
        app.final_decision = decision
        app.decision_reason = reason
        if officer_notes is not None:
            app.officer_notes = officer_notes

        # Mirror decision into status
        decision_to_status = {
            FinalDecision.APPROVED: ApplicationStatus.APPROVED,
            FinalDecision.REJECTED: ApplicationStatus.REJECTED,
            FinalDecision.MANUAL_REVIEW: ApplicationStatus.MANUAL_REVIEW,
        }
        if decision in decision_to_status:
            app.status = decision_to_status[decision]

        self._db.flush()
        return app

    def mark_pipeline_stage(self, app: Application, stage: str) -> Application:
        """
        Mark a pipeline stage as complete.
        stage: one of ocr_completed | ratios_calculated | rules_evaluated |
                       ml_predicted | report_generated
        """
        valid_stages = {
            "ocr_completed": ApplicationStatus.OCR_COMPLETE,
            "ratios_calculated": ApplicationStatus.RATIO_CALCULATED,
            "rules_evaluated": ApplicationStatus.RULE_EVALUATED,
            "ml_predicted": ApplicationStatus.ML_PREDICTED,
            "report_generated": ApplicationStatus.REPORT_GENERATED,
        }
        if stage not in valid_stages:
            raise ValueError(f"Unknown pipeline stage: {stage}")
        setattr(app, stage, True)
        # A decided or withdrawn application keeps its outcome — re-running a
        # pipeline step (e.g. regenerating a report) must not reopen it.
        if app.status not in _TERMINAL_STATUSES:
            app.status = valid_stages[stage]
        self._db.flush()
        return app
