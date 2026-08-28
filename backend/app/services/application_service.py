"""
ApplicationService — loan application lifecycle business logic.

Responsibilities:
  - Create / update / submit / withdraw applications
  - Generate unique application reference numbers  (CLA-YYYYMMDD-NNNNN)
  - Enforce state-machine transitions (can only submit a DRAFT, etc.)
  - Record every state change in audit_logs
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.logging import get_logger
from app.models.application import Application, ApplicationStatus, FinalDecision
from app.models.audit_log import AuditAction
from app.models.user import User, UserRole
from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDecisionUpdate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# States that allow editing
# ---------------------------------------------------------------------------
_EDITABLE_STATES = {ApplicationStatus.DRAFT, ApplicationStatus.UNDER_REVIEW}

# ---------------------------------------------------------------------------
# States that allow withdrawal
# ---------------------------------------------------------------------------
_WITHDRAWABLE_STATES = {
    ApplicationStatus.DRAFT,
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.OCR_PROCESSING,
    ApplicationStatus.OCR_COMPLETE,
    ApplicationStatus.RATIO_CALCULATED,
    ApplicationStatus.RULE_EVALUATED,
}


class ApplicationService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = ApplicationRepository(db)
        self._company_repo = CompanyRepository(db)
        self._audit = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Application number generator
    # -------------------------------------------------------------------------

    def _generate_application_number(self) -> str:
        """
        Generate a unique sequential reference number.
        Format: CLA-YYYYMMDD-NNNNN  (e.g. CLA-20240115-00001)
        """
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        seq = self._repo.get_next_sequence_number(today)
        return f"CLA-{today}-{seq:05d}"

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, app_id: uuid.UUID) -> Application:
        app = self._repo.get_by_id(app_id)
        if not app:
            raise NotFoundError(message=f"Application '{app_id}' not found.")
        return app

    def get_response(self, app_id: uuid.UUID) -> ApplicationResponse:
        return ApplicationResponse.from_orm_with_relations(self.get_by_id(app_id))

    def list_applications(
        self,
        page: int = 1,
        page_size: int = 20,
        company_id: Optional[uuid.UUID] = None,
        status: Optional[ApplicationStatus] = None,
        final_decision: Optional[FinalDecision] = None,
        assigned_officer_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        current_user: Optional[User] = None,
    ) -> ApplicationListResponse:
        officer_filter = None

        apps, total = self._repo.list(
            page=page,
            page_size=page_size,
            company_id=company_id,
            status=status,
            final_decision=final_decision,
            assigned_officer_id=assigned_officer_id or officer_filter,
            search=search,
        )
        total_pages = max(1, math.ceil(total / page_size))
        return ApplicationListResponse(
            items=[ApplicationResponse.from_orm_with_relations(a) for a in apps],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_dashboard_stats(self) -> dict:
        return self._repo.dashboard_stats()

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def create_application(
        self,
        data: ApplicationCreate,
        created_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Application:
        # Verify the company exists and is active
        company = self._company_repo.get_by_id(data.company_id)
        if not company:
            raise NotFoundError(message=f"Company '{data.company_id}' not found.")
        if company.status.value in ("inactive", "blacklisted"):
            raise BadRequestError(
                message=f"Cannot create application for a company with status '{company.status.value}'."
            )

        app_number = self._generate_application_number()

        app = self._repo.create(
            application_number=app_number,
            company_id=data.company_id,
            loan_amount_requested=data.loan_amount_requested,
            loan_purpose=data.loan_purpose,
            loan_tenure_months=data.loan_tenure_months,
            interest_rate_requested=data.interest_rate_requested,
            collateral_description=data.collateral_description,
            collateral_value=data.collateral_value,
            officer_notes=data.officer_notes,
            status=ApplicationStatus.DRAFT,
            final_decision=FinalDecision.PENDING,
        )

        self._audit.log(
            action=AuditAction.APPLICATION_CREATED,
            description=f"Application {app_number} created for company '{company.name}'.",
            user_id=created_by.id,
            entity_type="application",
            entity_id=str(app.id),
            new_values={
                "application_number": app_number,
                "company": company.name,
                "loan_amount": float(data.loan_amount_requested),
                "purpose": data.loan_purpose.value,
            },
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Application created",
            extra={"app_id": str(app.id), "number": app_number, "company": company.name},
        )
        return app

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def update_application(
        self,
        app_id: uuid.UUID,
        data: ApplicationUpdate,
        updated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Application:
        app = self.get_by_id(app_id)

        if app.status not in _EDITABLE_STATES:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' cannot be edited in "
                    f"status '{app.status.value}'. Only DRAFT and UNDER_REVIEW "
                    f"applications are editable."
                )
            )

        old = {
            "loan_amount": float(app.loan_amount_requested),
            "purpose": app.loan_purpose.value,
        }
        updates = data.model_dump(exclude_none=True)
        self._repo.update(app, **updates)

        self._audit.log(
            action=AuditAction.APPLICATION_UPDATED,
            description=f"Application {app.application_number} updated.",
            user_id=updated_by.id,
            entity_type="application",
            entity_id=str(app.id),
            old_values=old,
            new_values=updates,
            ip_address=ip_address,
            request_id=request_id,
        )
        return app

    # -------------------------------------------------------------------------
    # Submit
    # -------------------------------------------------------------------------

    def submit_application(
        self,
        app_id: uuid.UUID,
        submitted_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Application:
        app = self.get_by_id(app_id)

        if app.status != ApplicationStatus.DRAFT:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' is already in status "
                    f"'{app.status.value}'. Only DRAFT applications can be submitted."
                )
            )

        # Ensure at least one document is attached before submission
        doc_count = app.documents.count()
        if doc_count == 0:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' has no documents attached. "
                    f"Upload at least one financial document before submitting."
                )
            )

        self._repo.update_status(app, ApplicationStatus.SUBMITTED)

        self._audit.log(
            action=AuditAction.APPLICATION_SUBMITTED,
            description=f"Application {app.application_number} submitted for review.",
            user_id=submitted_by.id,
            entity_type="application",
            entity_id=str(app.id),
            old_values={"status": "draft"},
            new_values={"status": "submitted"},
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info("Application submitted", extra={"app_id": str(app.id)})
        return app

    # -------------------------------------------------------------------------
    # Record final decision
    # -------------------------------------------------------------------------

    def record_decision(
        self,
        app_id: uuid.UUID,
        data: ApplicationDecisionUpdate,
        decided_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Application:
        app = self.get_by_id(app_id)

        # A decision can only be recorded once the ML prediction is done
        # (unless the application was rejected by the rule engine)
        allowed_pre_decision_statuses = {
            ApplicationStatus.RULE_EVALUATED,
            ApplicationStatus.ML_PREDICTED,
            ApplicationStatus.REPORT_GENERATED,
            ApplicationStatus.MANUAL_REVIEW,
        }
        if app.status not in allowed_pre_decision_statuses:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' cannot receive a decision "
                    f"in status '{app.status.value}'. The assessment pipeline must "
                    f"complete first."
                )
            )

        old_decision = app.final_decision.value
        self._repo.update_decision(
            app,
            decision=data.decision,
            reason=data.decision_reason,
            officer_notes=data.officer_notes,
        )

        self._audit.log(
            action=AuditAction.DECISION_MADE,
            description=(
                f"Decision '{data.decision.value}' recorded for application "
                f"{app.application_number} by '{decided_by.email}'."
            ),
            user_id=decided_by.id,
            entity_type="application",
            entity_id=str(app.id),
            old_values={"decision": old_decision},
            new_values={"decision": data.decision.value, "reason": data.decision_reason},
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info(
            "Decision recorded",
            extra={
                "app_id": str(app.id),
                "decision": data.decision.value,
                "officer": decided_by.email,
            },
        )
        return app

    # -------------------------------------------------------------------------
    # Withdraw
    # -------------------------------------------------------------------------

    def withdraw_application(
        self,
        app_id: uuid.UUID,
        withdrawn_by: User,
        reason: Optional[str] = None,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Application:
        app = self.get_by_id(app_id)

        if app.status not in _WITHDRAWABLE_STATES:
            raise BadRequestError(
                message=(
                    f"Application '{app.application_number}' cannot be withdrawn "
                    f"in status '{app.status.value}'."
                )
            )

        old_status = app.status.value
        self._repo.update(app, status=ApplicationStatus.WITHDRAWN)
        if reason:
            self._repo.update(app, decision_reason=reason)

        self._audit.log(
            action=AuditAction.APPLICATION_WITHDRAWN,
            description=f"Application {app.application_number} withdrawn. Reason: {reason or 'N/A'}",
            user_id=withdrawn_by.id,
            entity_type="application",
            entity_id=str(app.id),
            old_values={"status": old_status},
            new_values={"status": "withdrawn", "reason": reason},
            ip_address=ip_address,
            request_id=request_id,
        )
        return app

    # -------------------------------------------------------------------------
    # Assign officer
    # -------------------------------------------------------------------------

    def assign_officer(
        self,
        app_id: uuid.UUID,
        officer_id: uuid.UUID,
        assigned_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Application:
        app = self.get_by_id(app_id)
        old_officer = str(app.assigned_officer_id) if app.assigned_officer_id else None
        self._repo.update(
            app,
            assigned_officer_id=officer_id,
            status=ApplicationStatus.UNDER_REVIEW,
        )

        self._audit.log(
            action=AuditAction.APPLICATION_UPDATED,
            description=f"Application {app.application_number} assigned to officer {officer_id}.",
            user_id=assigned_by.id,
            entity_type="application",
            entity_id=str(app.id),
            old_values={"assigned_officer_id": old_officer},
            new_values={"assigned_officer_id": str(officer_id)},
            ip_address=ip_address,
            request_id=request_id,
        )
        return app
