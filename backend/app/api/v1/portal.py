"""
Company portal endpoints — company users view their own data.

All routes require COMPANY role and scope results to the caller's company_id.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.database.connection import get_db
from app.dependencies import get_current_user, get_client_ip
from app.models.application import Application, ApplicationStatus, FinalDecision
from app.models.company import Company
from app.models.document import Document
from app.models.user import User, UserRole
from app.schemas.auth import MessageResponse

router = APIRouter()


def _require_company(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.COMPANY:
        raise PermissionDeniedError(message="This endpoint is for company portal users only.")
    if not current_user.company_id:
        raise PermissionDeniedError(message="No company linked to your account.")
    return current_user


# ---------------------------------------------------------------------------
# GET /portal/company — view own company profile
# ---------------------------------------------------------------------------

@router.get("/company", summary="View your company profile")
def get_own_company(
    db: Session = Depends(get_db),
    user: User = Depends(_require_company),
) -> dict:
    company = db.query(Company).filter(Company.id == user.company_id).first()
    if not company:
        raise NotFoundError(message="Company not found.")
    return {
        "id": str(company.id),
        "name": company.name,
        "registration_number": company.registration_number,
        "company_type": company.company_type.value if company.company_type else None,
        "industry": company.industry.value if company.industry else None,
        "status": company.status.value,
        "incorporation_date": company.incorporation_date,
        "registered_address": company.registered_address,
        "city": company.city,
        "state": company.state,
        "postal_code": company.postal_code,
        "contact_email": company.contact_email,
        "contact_phone": company.contact_phone,
        "website": company.website,
        "annual_turnover": float(company.annual_turnover) if company.annual_turnover else None,
        "number_of_employees": company.number_of_employees,
        "created_at": company.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /portal/applications — list own applications
# ---------------------------------------------------------------------------

@router.get("/applications", summary="List your loan applications")
def list_own_applications(
    db: Session = Depends(get_db),
    user: User = Depends(_require_company),
    page: int = 1,
    page_size: int = 20,
) -> dict:
    q = (
        db.query(Application)
        .filter(Application.company_id == user.company_id)
        .order_by(Application.created_at.desc())
    )
    total = q.count()
    apps = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for a in apps:
        items.append({
            "id": str(a.id),
            "application_number": a.application_number,
            "loan_amount_requested": float(a.loan_amount_requested) if a.loan_amount_requested else 0,
            "loan_purpose": a.loan_purpose.value if a.loan_purpose else None,
            "loan_tenure_months": a.loan_tenure_months,
            "status": a.status.value,
            "final_decision": a.final_decision.value if a.final_decision else "pending",
            "risk_score": float(a.risk_score) if a.risk_score else None,
            "created_at": a.created_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
            "pipeline": {
                "ocr_completed": a.ocr_completed or False,
                "ratios_calculated": a.ratios_calculated or False,
                "rules_evaluated": a.rules_evaluated or False,
                "ml_predicted": a.ml_predicted or False,
                "report_generated": a.report_generated or False,
            },
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


# ---------------------------------------------------------------------------
# GET /portal/applications/{id} — application detail with timeline
# ---------------------------------------------------------------------------

@router.get("/applications/{application_id}", summary="View application detail and timeline")
def get_application_detail(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_require_company),
) -> dict:
    app = (
        db.query(Application)
        .filter(Application.id == application_id, Application.company_id == user.company_id)
        .first()
    )
    if not app:
        raise NotFoundError(message="Application not found.")

    timeline = _build_timeline(app)

    docs = db.query(Document).filter(Document.application_id == application_id).all()
    doc_list = [
        {
            "id": str(d.id),
            "document_type": d.document_type.value if d.document_type else None,
            "original_filename": d.original_filename,
            "status": d.status.value if d.status else None,
            "uploaded_at": d.created_at.isoformat(),
        }
        for d in docs
    ]

    return {
        "id": str(app.id),
        "application_number": app.application_number,
        "loan_amount_requested": float(app.loan_amount_requested) if app.loan_amount_requested else 0,
        "loan_purpose": app.loan_purpose.value if app.loan_purpose else None,
        "loan_tenure_months": app.loan_tenure_months,
        "interest_rate_requested": float(app.interest_rate_requested) if app.interest_rate_requested else None,
        "collateral_description": app.collateral_description,
        "collateral_value": float(app.collateral_value) if app.collateral_value else None,
        "status": app.status.value,
        "final_decision": app.final_decision.value if app.final_decision else "pending",
        "decision_reason": app.decision_reason,
        "risk_score": float(app.risk_score) if app.risk_score else None,
        "created_at": app.created_at.isoformat(),
        "updated_at": app.updated_at.isoformat(),
        "pipeline": {
            "ocr_completed": app.ocr_completed or False,
            "ratios_calculated": app.ratios_calculated or False,
            "rules_evaluated": app.rules_evaluated or False,
            "ml_predicted": app.ml_predicted or False,
            "report_generated": app.report_generated or False,
        },
        "timeline": timeline,
        "documents": doc_list,
    }


# ---------------------------------------------------------------------------
# GET /portal/dashboard — company dashboard stats
# ---------------------------------------------------------------------------

@router.get("/dashboard", summary="Company dashboard overview")
def portal_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(_require_company),
) -> dict:
    apps = (
        db.query(Application)
        .filter(Application.company_id == user.company_id)
        .all()
    )
    total = len(apps)
    approved = sum(1 for a in apps if a.final_decision == FinalDecision.APPROVED)
    rejected = sum(1 for a in apps if a.final_decision == FinalDecision.REJECTED)
    manual_review = sum(1 for a in apps if a.final_decision == FinalDecision.MANUAL_REVIEW)
    pending = sum(1 for a in apps if a.final_decision == FinalDecision.PENDING)
    in_pipeline = sum(1 for a in apps if a.status.value in (
        "submitted", "under_review", "ocr_processing", "ocr_complete",
        "ratio_calculated", "rule_evaluated", "ml_predicted",
    ))

    company = db.query(Company).filter(Company.id == user.company_id).first()

    return {
        "company_name": company.name if company else "Unknown",
        "company_status": company.status.value if company else "unknown",
        "total_applications": total,
        "approved": approved,
        "rejected": rejected,
        "manual_review": manual_review,
        "pending": pending,
        "in_pipeline": in_pipeline,
        "recent_applications": [
            {
                "id": str(a.id),
                "application_number": a.application_number,
                "status": a.status.value,
                "final_decision": a.final_decision.value if a.final_decision else "pending",
                "loan_amount": float(a.loan_amount_requested) if a.loan_amount_requested else 0,
                "created_at": a.created_at.isoformat(),
            }
            for a in sorted(apps, key=lambda x: x.created_at, reverse=True)[:5]
        ],
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_timeline(app: Application) -> list:
    stages = [
        ("Application Submitted", "submitted", app.status.value != "draft"),
        ("Documents Under OCR Processing", "ocr", app.ocr_completed or False),
        ("Financial Ratios Computed", "ratios", app.ratios_calculated or False),
        ("Credit Rules Evaluated", "rules", app.rules_evaluated or False),
        ("ML Risk Assessment Complete", "ml", app.ml_predicted or False),
        ("Credit Report Generated", "report", app.report_generated or False),
    ]

    decision_label = "Decision Pending"
    decision_complete = False
    if app.final_decision and app.final_decision != FinalDecision.PENDING:
        decision_label = f"Decision: {app.final_decision.value.replace('_', ' ').title()}"
        decision_complete = True
    stages.append((decision_label, "decision", decision_complete))

    completed_count = sum(1 for _, _, done in stages if done)
    timeline = []
    for label, key, done in stages:
        timeline.append({
            "label": label,
            "key": key,
            "completed": done,
            "current": not done and (len(timeline) == 0 or timeline[-1]["completed"]),
        })

    return timeline
