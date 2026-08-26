"""
Loan application endpoints — full lifecycle from creation to final decision.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import (
    PaginationParams,
    get_client_ip,
    get_current_user,
    get_pagination,
    require_analyst,
    require_officer,
)
from app.models.application import ApplicationStatus, FinalDecision
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDecisionUpdate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
from app.schemas.auth import MessageResponse
from app.services.application_service import ApplicationService

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /applications
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List loan applications",
)
def list_applications(
    company_id: Optional[uuid.UUID] = Query(default=None),
    app_status: Optional[ApplicationStatus] = Query(default=None, alias="status"),
    decision: Optional[FinalDecision] = Query(default=None),
    search: Optional[str] = Query(default=None),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationListResponse:
    service = ApplicationService(db)
    return service.list_applications(
        page=pagination.page,
        page_size=pagination.page_size,
        company_id=company_id,
        status=app_status,
        final_decision=decision,
        search=search,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# POST /applications
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new loan application",
)
def create_application(
    request: Request,
    body: ApplicationCreate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    service = ApplicationService(db)
    app = service.create_application(
        data=body,
        created_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(app.id)


# ---------------------------------------------------------------------------
# GET /applications/stats/dashboard
#
# Must stay above /{app_id} — FastAPI matches in declaration order and
# "stats" would otherwise be captured as an app_id.
# ---------------------------------------------------------------------------

@router.get(
    "/stats/dashboard",
    status_code=status.HTTP_200_OK,
    summary="Aggregate KPIs for the dashboard",
)
def dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return ApplicationService(db).get_dashboard_stats()


# ---------------------------------------------------------------------------
# GET /applications/{app_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{app_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a loan application by ID",
)
def get_application(
    app_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    return ApplicationService(db).get_response(app_id)


# ---------------------------------------------------------------------------
# PUT /applications/{app_id}
# ---------------------------------------------------------------------------

@router.put(
    "/{app_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a loan application (only DRAFT / UNDER_REVIEW)",
)
def update_application(
    request: Request,
    app_id: uuid.UUID,
    body: ApplicationUpdate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    service = ApplicationService(db)
    service.update_application(
        app_id=app_id,
        data=body,
        updated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(app_id)


# ---------------------------------------------------------------------------
# POST /applications/{app_id}/submit
# ---------------------------------------------------------------------------

@router.post(
    "/{app_id}/submit",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit a draft application for review",
)
def submit_application(
    request: Request,
    app_id: uuid.UUID,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    service = ApplicationService(db)
    service.submit_application(
        app_id=app_id,
        submitted_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(app_id)


# ---------------------------------------------------------------------------
# PATCH /applications/{app_id}/decision
# ---------------------------------------------------------------------------

@router.patch(
    "/{app_id}/decision",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Record the final credit decision (officer / admin only)",
)
def record_decision(
    request: Request,
    app_id: uuid.UUID,
    body: ApplicationDecisionUpdate,
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    service = ApplicationService(db)
    service.record_decision(
        app_id=app_id,
        data=body,
        decided_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(app_id)


# ---------------------------------------------------------------------------
# POST /applications/{app_id}/withdraw
# ---------------------------------------------------------------------------

class WithdrawBody(BaseModel):
    reason: Optional[str] = None


@router.post(
    "/{app_id}/withdraw",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Withdraw an application",
)
def withdraw_application(
    request: Request,
    app_id: uuid.UUID,
    body: WithdrawBody = WithdrawBody(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = ApplicationService(db)
    app = service.withdraw_application(
        app_id=app_id,
        withdrawn_by=current_user,
        reason=body.reason,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message=f"Application '{app.application_number}' has been withdrawn.")


# ---------------------------------------------------------------------------
# POST /applications/{app_id}/assign
# ---------------------------------------------------------------------------

class AssignBody(BaseModel):
    officer_id: uuid.UUID


@router.post(
    "/{app_id}/assign",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign an officer to a loan application (admin / officer only)",
)
def assign_officer(
    request: Request,
    app_id: uuid.UUID,
    body: AssignBody,
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
) -> ApplicationResponse:
    service = ApplicationService(db)
    service.assign_officer(
        app_id=app_id,
        officer_id=body.officer_id,
        assigned_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(app_id)



