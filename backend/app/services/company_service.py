"""
CompanyService — company management business logic.
"""

from __future__ import annotations

import math
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.models.audit_log import AuditAction
from app.models.company import Company, CompanyStatus, CompanyType, Industry
from app.models.user import User, UserRole
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.company_repository import CompanyRepository
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)

logger = get_logger(__name__)


class CompanyService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._repo = CompanyRepository(db)
        self._audit = AuditLogRepository(db)

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, company_id: uuid.UUID) -> Company:
        company = self._repo.get_by_id(company_id)
        if not company:
            raise NotFoundError(message=f"Company '{company_id}' not found.")
        return company

    def get_response(self, company_id: uuid.UUID) -> CompanyResponse:
        company = self.get_by_id(company_id)
        app_count = self._repo.count_applications(company_id)
        resp = CompanyResponse.model_validate(company)
        resp.application_count = app_count
        return resp

    def list_companies(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[CompanyStatus] = None,
        industry: Optional[Industry] = None,
        company_type: Optional[CompanyType] = None,
        search: Optional[str] = None,
    ) -> CompanyListResponse:
        companies, total = self._repo.list(
            page=page,
            page_size=page_size,
            status=status,
            industry=industry,
            company_type=company_type,
            search=search,
        )
        total_pages = max(1, math.ceil(total / page_size))
        items = []
        for c in companies:
            r = CompanyResponse.model_validate(c)
            r.application_count = self._repo.count_applications(c.id)
            items.append(r)
        return CompanyListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    def create_company(
        self,
        data: CompanyCreate,
        created_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Company:
        if self._repo.exists_by_registration_number(data.registration_number):
            raise ConflictError(
                message=f"A company with registration number "
                        f"'{data.registration_number}' already exists."
            )

        company = self._repo.create(
            name=data.name,
            registration_number=data.registration_number.upper(),
            tax_id=data.tax_id,
            gst_number=data.gst_number,
            company_type=data.company_type,
            industry=data.industry,
            status=CompanyStatus.ACTIVE,
            incorporation_date=data.incorporation_date,
            country_of_incorporation=data.country_of_incorporation,
            registered_address=data.registered_address,
            city=data.city,
            state=data.state,
            postal_code=data.postal_code,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            website=data.website,
            annual_turnover=data.annual_turnover,
            number_of_employees=data.number_of_employees,
            notes=data.notes,
        )

        self._audit.log(
            action=AuditAction.COMPANY_CREATED,
            description=f"Company '{company.name}' (Reg: {company.registration_number}) created.",
            user_id=created_by.id,
            entity_type="company",
            entity_id=str(company.id),
            new_values={"name": company.name, "registration_number": company.registration_number},
            ip_address=ip_address,
            request_id=request_id,
        )

        logger.info("Company created", extra={"company_id": str(company.id), "company_name": company.name})
        return company

    # -------------------------------------------------------------------------
    # Update
    # -------------------------------------------------------------------------

    def update_company(
        self,
        company_id: uuid.UUID,
        data: CompanyUpdate,
        updated_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Company:
        company = self.get_by_id(company_id)
        old = {"name": company.name, "status": company.status.value}

        updates = data.model_dump(exclude_none=True)
        self._repo.update(company, **updates)

        self._audit.log(
            action=AuditAction.COMPANY_UPDATED,
            description=f"Company '{company.name}' updated by '{updated_by.email}'.",
            user_id=updated_by.id,
            entity_type="company",
            entity_id=str(company.id),
            old_values=old,
            new_values=updates,
            ip_address=ip_address,
            request_id=request_id,
        )
        return company

    # -------------------------------------------------------------------------
    # Deactivate (soft delete)
    # -------------------------------------------------------------------------

    def deactivate_company(
        self,
        company_id: uuid.UUID,
        deleted_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> Company:
        company = self.get_by_id(company_id)

        # Do not deactivate if there are active applications
        active_apps = self._repo.count_applications(company_id)
        if active_apps > 0:
            raise PermissionDeniedError(
                message=(
                    f"Cannot deactivate company '{company.name}' — "
                    f"it has {active_apps} associated loan application(s). "
                    f"Resolve all applications first."
                )
            )

        self._repo.soft_delete(company)

        self._audit.log(
            action=AuditAction.COMPANY_UPDATED,
            description=f"Company '{company.name}' deactivated by '{deleted_by.email}'.",
            user_id=deleted_by.id,
            entity_type="company",
            entity_id=str(company.id),
            old_values={"status": "active"},
            new_values={"status": "inactive"},
            ip_address=ip_address,
            request_id=request_id,
        )
        return company

    # -------------------------------------------------------------------------
    # Hard delete (admin only — removes company + all related data)
    # -------------------------------------------------------------------------

    def hard_delete_company(
        self,
        company_id: uuid.UUID,
        deleted_by: User,
        ip_address: str = "unknown",
        request_id: str = "unknown",
    ) -> str:
        """
        Permanently delete a company along with all applications, documents,
        OCR data, ratios, predictions, and reports.

        Executes raw SQL deletes so the DB-level ON DELETE CASCADE runs and
        the ORM's default "nullify FK" behavior is bypassed. Company users are
        detached (company_id -> NULL) and deactivated.
        """
        from sqlalchemy import text

        company = self.get_by_id(company_id)
        company_name = company.name

        # Detach any company users first so they are not deleted with the company
        self._db.execute(
            text(
                "UPDATE users SET company_id = NULL, status = 'inactive' "
                "WHERE company_id = :cid"
            ),
            {"cid": str(company_id)},
        )

        # Write the audit log BEFORE the delete so entity_id references still make sense
        self._audit.log(
            action=AuditAction.COMPANY_UPDATED,
            description=f"Company '{company_name}' permanently deleted by '{deleted_by.email}'.",
            user_id=deleted_by.id,
            entity_type="company",
            entity_id=str(company_id),
            old_values={"name": company_name},
            new_values={"deleted": True},
            ip_address=ip_address,
            request_id=request_id,
        )

        # Flush the audit log and the user detach; then drop the ORM identity
        # for the company to prevent SQLAlchemy from emitting a cascade UPDATE
        # that would try to null out loan_applications.company_id.
        self._db.flush()
        self._db.expunge(company)

        # DB-level cascade drops loan_applications -> documents -> ocr_data,
        # financial_ratios, predictions, reports in one shot.
        self._db.execute(
            text("DELETE FROM companies WHERE id = :cid"),
            {"cid": str(company_id)},
        )

        self._db.commit()
        logger.info(
            "Company hard-deleted",
            extra={"company_id": str(company_id), "company_name": company_name},
        )
        return company_name
