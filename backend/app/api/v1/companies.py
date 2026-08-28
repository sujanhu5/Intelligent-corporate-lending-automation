"""
Company management endpoints — CRUD + company-level application listing.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.dependencies import (
    PaginationParams,
    get_client_ip,
    get_current_user,
    get_pagination,
    require_admin,
    require_analyst,
    require_officer,
)
from app.models.company import CompanyStatus, CompanyType, Industry
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.application import ApplicationSummary
from app.schemas.company import (
    CompanyCreate,
    CompanyListResponse,
    CompanyResponse,
    CompanyUpdate,
)
from app.services.company_service import CompanyService
from app.repositories.application_repository import ApplicationRepository

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /companies
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=CompanyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all companies",
)
def list_companies(
    status: Optional[CompanyStatus] = Query(default=None),
    industry: Optional[Industry] = Query(default=None),
    company_type: Optional[CompanyType] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search name, reg. number, city"),
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyListResponse:
    service = CompanyService(db)
    return service.list_companies(
        page=pagination.page,
        page_size=pagination.page_size,
        status=status,
        industry=industry,
        company_type=company_type,
        search=search,
    )


# ---------------------------------------------------------------------------
# POST /companies
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new company",
)
def create_company(
    request: Request,
    body: CompanyCreate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    service = CompanyService(db)
    company = service.create_company(
        data=body,
        created_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(company.id)


# ---------------------------------------------------------------------------
# GET /companies/{company_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get company details",
)
def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    return CompanyService(db).get_response(company_id)


# ---------------------------------------------------------------------------
# PUT /companies/{company_id}
# ---------------------------------------------------------------------------

@router.put(
    "/{company_id}",
    response_model=CompanyResponse,
    status_code=status.HTTP_200_OK,
    summary="Update company information",
)
def update_company(
    request: Request,
    company_id: uuid.UUID,
    body: CompanyUpdate,
    current_user: User = Depends(require_analyst),
    db: Session = Depends(get_db),
) -> CompanyResponse:
    service = CompanyService(db)
    service.update_company(
        company_id=company_id,
        data=body,
        updated_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return service.get_response(company_id)


# ---------------------------------------------------------------------------
# DELETE /companies/{company_id}  (soft delete — admin only)
# ---------------------------------------------------------------------------

@router.delete(
    "/{company_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a company (admin only)",
)
def deactivate_company(
    request: Request,
    company_id: uuid.UUID,
    current_user: User = Depends(require_officer),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = CompanyService(db)
    company = service.deactivate_company(
        company_id=company_id,
        deleted_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message=f"Company '{company.name}' has been deactivated.")


# ---------------------------------------------------------------------------
# DELETE /companies/{company_id}/permanent  (hard delete — admin only)
# ---------------------------------------------------------------------------

@router.delete(
    "/{company_id}/permanent",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Permanently delete a company and all related data (admin only)",
)
def hard_delete_company(
    request: Request,
    company_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> MessageResponse:
    service = CompanyService(db)
    name = service.hard_delete_company(
        company_id=company_id,
        deleted_by=current_user,
        ip_address=get_client_ip(request),
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    return MessageResponse(message=f"Company '{name}' and all associated data permanently deleted.")


# ---------------------------------------------------------------------------
# GET /companies/{company_id}/applications
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/applications",
    response_model=list[ApplicationSummary],
    status_code=status.HTTP_200_OK,
    summary="List all loan applications for a company",
)
def get_company_applications(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    # Verify company exists
    CompanyService(db).get_by_id(company_id)
    apps = ApplicationRepository(db).get_by_company(company_id)
    return [ApplicationSummary.model_validate(a) for a in apps]

