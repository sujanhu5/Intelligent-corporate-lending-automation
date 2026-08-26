"""
CompanyRepository — all database operations for the companies table.
"""

from __future__ import annotations

import math
import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.company import Company, CompanyStatus, CompanyType, Industry


class CompanyRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # -------------------------------------------------------------------------
    # Read
    # -------------------------------------------------------------------------

    def get_by_id(self, company_id: uuid.UUID) -> Optional[Company]:
        return self._db.query(Company).filter(Company.id == company_id).first()

    def get_by_registration_number(self, reg_number: str) -> Optional[Company]:
        return (
            self._db.query(Company)
            .filter(Company.registration_number == reg_number.strip().upper())
            .first()
        )

    def list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[CompanyStatus] = None,
        industry: Optional[Industry] = None,
        company_type: Optional[CompanyType] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Company], int]:
        q = self._db.query(Company)

        if status:
            q = q.filter(Company.status == status)
        if industry:
            q = q.filter(Company.industry == industry)
        if company_type:
            q = q.filter(Company.company_type == company_type)
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(
                or_(
                    Company.name.ilike(like),
                    Company.registration_number.ilike(like),
                    Company.gst_number.ilike(like),
                    Company.city.ilike(like),
                )
            )

        total = q.count()
        offset = (page - 1) * page_size
        companies = (
            q.order_by(Company.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return companies, total

    def exists_by_registration_number(self, reg_number: str) -> bool:
        return (
            self._db.query(Company.id)
            .filter(Company.registration_number == reg_number.strip().upper())
            .first()
        ) is not None

    def count_applications(self, company_id: uuid.UUID) -> int:
        from app.models.application import Application
        return (
            self._db.query(func.count(Application.id))
            .filter(Application.company_id == company_id)
            .scalar()
            or 0
        )

    # -------------------------------------------------------------------------
    # Write
    # -------------------------------------------------------------------------

    def create(self, **kwargs) -> Company:
        company = Company(**kwargs)
        self._db.add(company)
        self._db.flush()
        return company

    def update(self, company: Company, **fields) -> Company:
        for key, value in fields.items():
            if hasattr(company, key) and value is not None:
                setattr(company, key, value)
        self._db.flush()
        return company

    def set_status(self, company: Company, status: CompanyStatus) -> Company:
        company.status = status
        self._db.flush()
        return company

    def soft_delete(self, company: Company) -> Company:
        company.status = CompanyStatus.INACTIVE
        self._db.flush()
        return company
